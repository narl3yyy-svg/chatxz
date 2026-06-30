from chatxz.core.audio.prefs import (
    AUDIO_DEVICE_AUTO,
    is_input_pinned,
    is_output_pinned,
    normalize_prefs,
    resolve_device_index,
)


class FakePa:
    def get_device_count(self):
        return 2

    def get_device_info_by_index(self, i):
        if i == 0:
            return {"name": "HDA Analog (hw:0,0)", "maxInputChannels": 2, "maxOutputChannels": 2}
        return {"name": "HDA HDMI (hw:0,7)", "maxInputChannels": 0, "maxOutputChannels": 8}


def test_normalize_prefs_auto():
    p = normalize_prefs({})
    assert p["audio_input_device"] == AUDIO_DEVICE_AUTO
    assert not p["pin_input"]
    assert not p["pin_output"]


def test_is_input_pinned_by_index():
    assert is_input_pinned({"audio_input_device": 1})
    assert not is_input_pinned({"audio_input_device": -1})


def test_is_output_pinned_by_pulse_sink():
    assert is_output_pinned({"audio_pulse_sink": "alsa_output.hdmi"})


def test_resolve_device_index_by_name():
    ranked = [(0, "HDA Analog (hw:0,0)", 90), (1, "HDA Alt (hw:0,2)", 80)]
    idx, name = resolve_device_index(
        FakePa(),
        input_device=True,
        index=-1,
        name="Alt",
        ranked=ranked,
    )
    assert idx == 1
    assert "Alt" in name


def test_resolve_device_index_by_index():
    ranked = [(0, "HDA Analog (hw:0,0)", 90)]
    idx, name = resolve_device_index(
        FakePa(),
        input_device=False,
        index=0,
        name="",
        ranked=ranked,
    )
    assert idx == 0