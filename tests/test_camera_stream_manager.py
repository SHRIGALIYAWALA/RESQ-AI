from backend.vision.stream_manager import CameraStream


class FakeCapture:
    def __init__(self, opened):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True

    def set(self, _property, _value):
        return True


class FakeCv2:
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4

    def __init__(self, capture):
        self.capture = capture

    def VideoCapture(self, _source):
        return self.capture


def make_stream():
    stream = CameraStream.__new__(CameraStream)
    stream.camera_id = "test-camera"
    stream.source = "http://127.0.0.1:8080/video"
    stream.source_type = "http"
    stream.last_error = None
    return stream


def test_failed_video_capture_is_released_and_has_diagnostic():
    capture = FakeCapture(opened=False)
    stream = make_stream()

    result = stream._open_capture(FakeCv2(capture))

    assert result is None
    assert capture.released is True
    assert "could not open" in stream.last_error.lower()


def test_successful_video_capture_clears_previous_diagnostic():
    capture = FakeCapture(opened=True)
    stream = make_stream()
    stream.last_error = "previous failure"

    result = stream._open_capture(FakeCv2(capture))

    assert result is capture
    assert stream.last_error is None
