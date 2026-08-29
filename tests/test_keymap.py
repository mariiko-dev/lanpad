from evdev import ecodes as E

from lanpad import keymap


def test_lowercase_letter_needs_no_shift():
    assert keymap.CHARMAP["a"] == (E.KEY_A, False)


def test_uppercase_letter_needs_shift():
    assert keymap.CHARMAP["A"] == (E.KEY_A, True)


def test_shifted_digit_maps_to_digit_key():
    assert keymap.CHARMAP["!"] == (E.KEY_1, True)


def test_named_key_lookup_is_case_insensitive():
    assert keymap.code_for("Escape") == E.KEY_ESC
    assert keymap.code_for("escape") == E.KEY_ESC


def test_code_for_accepts_single_character():
    assert keymap.code_for("v") == E.KEY_V


def test_code_for_returns_none_for_unknown():
    assert keymap.code_for("несуществующая") is None


def test_media_keys_present():
    for name in ("play", "next", "prev", "volup", "voldown", "mute"):
        assert keymap.code_for(name) is not None


def test_all_key_codes_includes_mouse_buttons():
    codes = keymap.all_key_codes()
    assert E.BTN_LEFT in codes
    assert E.BTN_RIGHT in codes
    assert E.BTN_MIDDLE in codes
    assert codes == sorted(set(codes))
