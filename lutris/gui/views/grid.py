"""Grid view for the main window"""

# pylint: disable=no-member
from gettext import gettext as _

from gi.repository import Gdk, GLib, Gtk

from lutris import settings
from lutris.gui.views import COL_ID, COL_INSTALLED, COL_MEDIA_PATHS, COL_NAME, COL_PLATFORM
from lutris.gui.views.animation import Transition
from lutris.gui.views.base import GameView
from lutris.gui.widgets.cellrenderers import GridViewCellRendererImage, GridViewCellRendererText
from lutris.services import SERVICES
from lutris.util.log import logger
from lutris.util.strings import gtk_safe


class GameGridView(Gtk.IconView, GameView):  # type:ignore[misc]
    __gsignals__ = GameView.__gsignals__

    min_width = 70  # Minimum width for a cell

    def __init__(self, store, hide_text=False):
        Gtk.IconView.__init__(self)
        GameView.__init__(self)
        self._hovered_game_id = None
        self._hover_transitions = {}
        self._scroll_transition = None
        self._animation_tick_id = 0
        self._pointer_inside = False
        self._scroll_adjustment = None
        self._scroll_handler_id = 0
        self._applying_scroll = False

        Gtk.IconView.set_selection_mode(self, Gtk.SelectionMode.MULTIPLE)
        self.get_style_context().add_class("library-grid")
        self.set_column_spacing(16)
        self.set_row_spacing(20)
        self.set_margin(20)
        self._show_badges = True

        if settings.SHOW_MEDIA:
            self.image_renderer = GridViewCellRendererImage()
            # Reserve the largest size once. Animation never changes the grid
            # layout or clips artwork against neighbouring cells.
            self.image_renderer.hover_zoom = 1.08
            self.pack_start(self.image_renderer, False)
            self._initialize_image_renderer_attributes()
        else:
            self.image_renderer = None
        self.set_item_padding(6)
        if hide_text:
            self.text_renderer = None
        else:
            self.text_renderer = GridViewCellRendererText()
            self.pack_end(self.text_renderer, False)
            self.set_cell_data_func(self.text_renderer, self.render_caption)

        self.set_game_store(store)

        self.connect_signals()
        self.connect("item-activated", self.on_item_activated)
        self.connect("selection-changed", self.on_selection_changed)
        self.connect("style-updated", self.on_style_updated)
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.connect("motion-notify-event", self.on_pointer_motion)
        self.connect("leave-notify-event", self.on_pointer_leave)
        self.connect("scroll-event", self.on_grid_scroll)
        self.connect("notify::vadjustment", self._bind_scroll_adjustment)
        self.connect("unmap", self._stop_animations)
        self.connect("destroy", self._dispose_animations)
        self._bind_scroll_adjustment()

    def _animations_enabled(self):
        return self.get_settings().get_property("gtk-enable-animations")

    @staticmethod
    def _animation_time():
        return GLib.get_monotonic_time() / 1_000_000

    def _ensure_animation_tick(self):
        if not self._animation_tick_id:
            self._animation_tick_id = self.add_tick_callback(self._animate)

    def _set_hovered_game(self, game_id):
        if game_id == self._hovered_game_id or not self.image_renderer:
            return
        now = self._animation_time()
        previous_id = self._hovered_game_id
        self._hovered_game_id = game_id
        for changed_id, target in ((previous_id, 0.0), (game_id, 1.0)):
            if changed_id is None:
                continue
            if not self._animations_enabled():
                self._hover_transitions.pop(changed_id, None)
                self.image_renderer.set_hover_fraction(changed_id, target)
            elif changed_id in self._hover_transitions:
                self._hover_transitions[changed_id] = self._hover_transitions[changed_id].retarget(target, now)
            else:
                start = self.image_renderer.hover_fractions.get(changed_id, 0.0)
                self._hover_transitions[changed_id] = Transition(start, target, now)
        self.queue_draw()
        if self._hover_transitions:
            self._ensure_animation_tick()

    def on_pointer_motion(self, _widget, event):
        self._pointer_inside = True
        # Motion events come from IconView's private scrolling window. Convert
        # root coordinates instead of relying on that unexposed GTK window.
        window = self.get_window()
        if not window:
            return False
        _, origin_x, origin_y = window.get_origin()
        x, y = self.convert_widget_to_bin_window_coords(int(event.x_root - origin_x), int(event.y_root - origin_y))
        path = self.get_path_at_pos(int(x), int(y))
        self._set_hovered_game(self.get_game_id_for_path(path) if path is not None else None)
        return False

    def on_pointer_leave(self, _widget, _event):
        self._pointer_inside = False
        self._set_hovered_game(None)
        return False

    def _update_pointer_hover(self):
        window = self.get_window()
        display = self.get_display()
        seat = display.get_default_seat() if display else None
        pointer = seat.get_pointer() if seat else None
        if self._pointer_inside and window and pointer:
            _, x, y, _ = window.get_device_position(pointer)
            x, y = self.convert_widget_to_bin_window_coords(x, y)
            path = self.get_path_at_pos(x, y)
            self._set_hovered_game(self.get_game_id_for_path(path) if path is not None else None)

    def _bind_scroll_adjustment(self, *_args):
        if self._scroll_adjustment and self._scroll_handler_id:
            self._scroll_adjustment.disconnect(self._scroll_handler_id)
        self._scroll_adjustment = self.get_vadjustment()
        self._scroll_transition = None
        self._scroll_handler_id = (
            self._scroll_adjustment.connect("value-changed", self._on_scroll_position_changed)
            if self._scroll_adjustment
            else 0
        )

    def _on_scroll_position_changed(self, _adjustment):
        # Scrollbar drags and keyboard/touchpad scrolling take precedence over
        # an unfinished wheel animation.
        if not self._applying_scroll:
            self._scroll_transition = None
        self._update_pointer_hover()

    def on_grid_scroll(self, _widget, event):
        if event.direction not in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            # Touchpads already provide continuous deltas; leave GTK's native
            # kinetic scrolling and horizontal gestures intact.
            self._scroll_transition = None
            return False
        if event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.MOD1_MASK):
            return False
        adjustment = self.get_vadjustment()
        if not adjustment or not self._animations_enabled():
            self._scroll_transition = None
            return False
        lower = adjustment.get_lower()
        upper = max(lower, adjustment.get_upper() - adjustment.get_page_size())
        if upper <= lower:
            return False
        current = adjustment.get_value()
        step = max(24.0, adjustment.get_page_size() ** (2 / 3))
        delta = -step if event.direction == Gdk.ScrollDirection.UP else step
        target = self._scroll_transition.target if self._scroll_transition else current
        if delta * (target - current) < 0:
            target = current
        target = min(upper, max(lower, target + delta))
        self._scroll_transition = Transition(current, target, self._animation_time(), 0.16)
        self._ensure_animation_tick()
        return True

    def _animate(self, _widget, frame_clock):
        now = frame_clock.get_frame_time() / 1_000_000
        for game_id, transition in list(self._hover_transitions.items()):
            self.image_renderer.set_hover_fraction(game_id, transition.value_at(now))
            if transition.finished(now):
                del self._hover_transitions[game_id]
        if self._scroll_transition and self._scroll_adjustment:
            transition = self._scroll_transition
            self._applying_scroll = True
            try:
                self._scroll_adjustment.set_value(transition.value_at(now))
            finally:
                self._applying_scroll = False
            if self._scroll_transition is transition and transition.finished(now):
                self._scroll_transition = None
        self.queue_draw()
        if self._hover_transitions or self._scroll_transition:
            return True
        self._animation_tick_id = 0
        return False

    def _stop_animations(self, *_args):
        if self._animation_tick_id:
            self.remove_tick_callback(self._animation_tick_id)
            self._animation_tick_id = 0
        self._hovered_game_id = None
        self._hover_transitions.clear()
        self._scroll_transition = None
        self._pointer_inside = False
        if self.image_renderer:
            self.image_renderer.hover_fractions.clear()
        self.queue_draw()

    def _dispose_animations(self, *_args):
        self._stop_animations()
        if self._scroll_adjustment and self._scroll_handler_id:
            self._scroll_adjustment.disconnect(self._scroll_handler_id)
            self._scroll_handler_id = 0

    def render_caption(self, _layout, renderer, model, iterator):
        game_id = model.get_value(iterator, COL_ID)
        name = model.get_value(iterator, COL_NAME)
        service_id = self.game_store.sources_by_id.get(game_id)
        service = SERVICES.get(service_id)
        source = service.name if service else _("Local game")
        state = _("Installed") if model.get_value(iterator, COL_INSTALLED) else _("Not installed")
        renderer.props.markup = '%s\n<span size="small" foreground="#a2b5ca">%s · %s</span>' % (
            name,
            gtk_safe(source),
            gtk_safe(state),
        )

    def set_game_store(self, game_store):
        self._stop_animations()
        super().set_game_store(game_store)
        self.model = game_store.store
        self.set_model(self.model)

        size = game_store.service_media.size
        if self.image_renderer:
            self.image_renderer.set_expected_size(size[0], size[1])
        if self.text_renderer:
            cell_width = max(size[0], self.min_width)
            self.text_renderer.set_width(cell_width)

    @property
    def show_badges(self):
        return self._show_badges

    @show_badges.setter
    def show_badges(self, value):
        if self._show_badges != value:
            self._show_badges = value
            self._initialize_image_renderer_attributes()
            self.queue_draw()

    def _initialize_image_renderer_attributes(self):
        if self.image_renderer:
            self.image_renderer.show_badges = self.show_badges
            self.clear_attributes(self.image_renderer)
            self.add_attribute(self.image_renderer, "game_id", COL_ID)
            self.add_attribute(self.image_renderer, "media_paths", COL_MEDIA_PATHS)
            self.add_attribute(self.image_renderer, "platform", COL_PLATFORM)
            self.add_attribute(self.image_renderer, "is_installed", COL_INSTALLED)

    def get_path_at(self, x, y):
        return self.get_path_at_pos(x, y)

    def set_selected(self, paths, scroll_into_view=False):
        self.unselect_all()

        for idx, path in enumerate(paths):
            self.select_path(path)
            if scroll_into_view and idx == 0:
                self.scroll_to_path(path, False, 0.0, 0.0)

    def get_selected(self):
        """Return list of all selected items"""
        return self.get_selected_items()

    def get_game_id_for_path(self, path):
        iterator = self.get_model().get_iter(path)
        return self.get_model().get_value(iterator, COL_ID)

    def get_path_for_game_id(self, game_id):
        if self.game_store:
            return self.game_store.get_path_by_id(game_id)
        return None

    def on_item_activated(self, _view, _path):
        """Handles double clicks"""
        selected_id = self.get_selected_game_id()
        if selected_id:
            logger.debug("Item activated: %s", selected_id)
            self.emit("game-activated", selected_id)

    def on_selection_changed(self, _view):
        """Handles selection changes"""
        selected_items = self.get_selected()
        self.emit("game-selected", selected_items)

    def on_style_updated(self, widget):
        if self.text_renderer:
            self.text_renderer.clear_caches()
