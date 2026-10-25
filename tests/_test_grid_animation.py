"""Timing, interruption and GTK integration of the library's grid effects."""

import unittest
from types import SimpleNamespace

from gi.repository import Gdk, GLib, Gtk

from lutris.gui.views.animation import Transition
from lutris.gui.views.grid import GameGridView
from lutris.gui.views.store import GameStore
from lutris.services.base import LutrisCoverartMedium


class TransitionTest(unittest.TestCase):
    def test_reversing_keeps_the_current_position_and_settles_at_target(self):
        original = Transition(0, 1, 10)
        reversed_transition = original.retarget(0, 10.07)
        self.assertEqual(reversed_transition.value_at(10.07), original.value_at(10.07))
        samples = [reversed_transition.value_at(10.07 + step / 100) for step in range(25)]
        self.assertEqual(samples, sorted(samples, reverse=True))
        self.assertEqual(samples[-1], 0)

    def test_long_frame_pause_finishes_without_overshooting(self):
        transition = Transition(230, 15, 10, 0.16)
        self.assertEqual(transition.value_at(9), 230)
        self.assertEqual(transition.value_at(50), 15)
        self.assertTrue(transition.finished(50))


@unittest.skipUnless(Gtk.init_check()[0], "Grid animations need a display (run under xvfb-run)")
class GridAnimationTest(unittest.TestCase):
    def setUp(self):
        self.store = GameStore(None, LutrisCoverartMedium())
        for index in range(30):
            self.store.add_game(
                {
                    "id": str(index),
                    "service_id": None,
                    "name": f"Game {index}",
                    "slug": f"animation-test-{index}",
                    "installed": 0,
                    "runner": "linux",
                }
            )
        self.grid = GameGridView(self.store)
        self.window = Gtk.Window(default_width=420, default_height=350)
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.add(self.grid)
        self.window.add(self.scrolled)
        self.window.show_all()
        self.gtk_settings = self.grid.get_settings()
        self.original_animations = self.gtk_settings.get_property("gtk-enable-animations")
        self.gtk_settings.set_property("gtk-enable-animations", True)
        self.pump(0.06)

    def tearDown(self):
        self.gtk_settings.set_property("gtk-enable-animations", self.original_animations)
        self.window.destroy()
        self.pump(0.01)

    @staticmethod
    def pump(seconds):
        loop = GLib.MainLoop()
        GLib.timeout_add(int(seconds * 1000), lambda: (loop.quit(), False)[1])
        loop.run()

    def wheel(self, direction=Gdk.ScrollDirection.DOWN):
        return self.grid.on_grid_scroll(self.grid, SimpleNamespace(direction=direction, state=0))

    def test_hover_grows_holds_and_shrinks_without_changing_cell_geometry(self):
        before = self.grid.image_renderer.do_get_preferred_height(self.grid)
        self.grid._set_hovered_game("0")
        self.pump(0.07)
        self.assertGreater(self.grid.image_renderer.hover_fractions["0"], 0)
        self.assertLess(self.grid.image_renderer.hover_fractions["0"], 1)
        self.pump(0.2)
        self.assertEqual(self.grid.image_renderer.hover_fractions["0"], 1)
        self.assertEqual(self.grid._animation_tick_id, 0)
        self.pump(0.04)
        self.assertEqual(self.grid.image_renderer.hover_fractions["0"], 1)
        self.assertEqual(self.grid.image_renderer.do_get_preferred_height(self.grid), before)
        self.grid.on_pointer_leave(self.grid, None)
        self.pump(0.07)
        self.assertGreater(self.grid.image_renderer.hover_fractions["0"], 0)
        self.assertLess(self.grid.image_renderer.hover_fractions["0"], 1)
        self.pump(0.2)
        self.assertNotIn("0", self.grid.image_renderer.hover_fractions)

    def test_quick_hover_switch_does_not_leave_previous_tile_enlarged(self):
        self.grid._set_hovered_game("0")
        self.pump(0.06)
        self.grid._set_hovered_game("1")
        self.pump(0.05)
        self.grid._set_hovered_game("0")
        self.pump(0.23)
        self.assertEqual(self.grid.image_renderer.hover_fractions, {"0": 1})
        self.assertEqual(self.grid._animation_tick_id, 0)

    def test_pointer_coordinates_follow_scrolled_content(self):
        found, first = self.grid.get_cell_rect(Gtk.TreePath("0"), None)
        self.assertTrue(found)
        _, origin_x, origin_y = self.grid.get_window().get_origin()
        pointer = self.grid.get_display().get_default_seat().get_pointer()
        pointer.warp(self.grid.get_screen(), origin_x + first.x + 20, origin_y + first.y + 20)
        self.pump(0.06)
        self.assertEqual(self.grid._hovered_game_id, "0")
        next_row = None
        for index in range(1, 30):
            found, rectangle = self.grid.get_cell_rect(Gtk.TreePath(str(index)), None)
            if found and rectangle.y > first.y:
                next_row = str(index), rectangle
                break
        assert next_row is not None
        game_id, rectangle = next_row
        self.grid.get_vadjustment().set_value(rectangle.y - first.y)
        self.pump(0.23)
        self.assertEqual(self.grid._hovered_game_id, game_id)
        self.assertNotIn("0", self.grid.image_renderer.hover_fractions)

    def test_wheel_is_interpolated_accumulates_and_clamps_at_bottom(self):
        adjustment = self.grid.get_vadjustment()
        self.assertTrue(self.wheel())
        target = self.grid._scroll_transition.target
        self.assertEqual(adjustment.get_value(), 0)
        self.pump(0.06)
        self.assertGreater(adjustment.get_value(), 0)
        self.assertLess(adjustment.get_value(), target)
        self.assertTrue(self.wheel())
        self.assertGreater(self.grid._scroll_transition.target, target)
        self.pump(0.23)
        for _ in range(1000):
            self.wheel()
        self.pump(0.23)
        self.assertAlmostEqual(adjustment.get_value(), adjustment.get_upper() - adjustment.get_page_size())
        self.assertIsNone(self.grid._scroll_transition)
        self.assertEqual(self.grid._animation_tick_id, 0)

    def test_scrollbar_and_touchpad_interrupt_wheel_animation(self):
        self.wheel()
        self.pump(0.04)
        adjustment = self.grid.get_vadjustment()
        adjustment.set_value(10)
        self.pump(0.23)
        self.assertEqual(adjustment.get_value(), 10)
        self.wheel()
        self.assertFalse(self.wheel(Gdk.ScrollDirection.SMOOTH))
        self.assertIsNone(self.grid._scroll_transition)

    def test_reduced_motion_and_unmapping_stop_animation(self):
        self.gtk_settings.set_property("gtk-enable-animations", False)
        self.grid._set_hovered_game("0")
        self.assertEqual(self.grid.image_renderer.hover_fractions, {"0": 1})
        self.assertEqual(self.grid._animation_tick_id, 0)
        self.assertFalse(self.wheel())
        self.gtk_settings.set_property("gtk-enable-animations", True)
        self.grid._set_hovered_game("1")
        self.wheel()
        self.window.hide()
        self.assertEqual(self.grid._animation_tick_id, 0)
        self.assertEqual(self.grid.image_renderer.hover_fractions, {})
        self.assertIsNone(self.grid._scroll_transition)
