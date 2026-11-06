"""voice.keep_mic: what stays stubbed, and that a stand-in only steps aside for a live claim."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "app/init/nospy-lib.sh"
SHELL = os.environ.get("TEST_SHELL", "sh")
STAYS_STUBBED = ["voiceconductor", "voiceclick", "nlpmanager", "performer", "voiceinput_network",
                 "voiceinput_preprocessor", "voiceinput_hidraw", "voiceinput_sound", "com.webos.app.voice"]


def sh(script, conf="", **env):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp, "conf")
        path.write_text(conf, encoding="utf-8")
        out = subprocess.run(
            [SHELL, "-c", '. "$LIB"\nCONF="$C"\nANSWER_CLAIM_PREFIX="$T/claim"\n' + script],
            env=dict(os.environ, LIB=str(LIB), C=str(path).replace("\\", "/"),
                     T=tmp.replace("\\", "/"), **env),
            capture_output=True, text=True)
    return out


def names(conf):
    out = sh("voice_execs", conf).stdout.split()
    return {path.rsplit("/", 1)[1] for path in out}


class TargetsTest(unittest.TestCase):
    def test_off_by_default(self):
        self.assertIn("voiceinput", names(""))
        self.assertEqual(sh("voice_units").stdout.split(), ["voiceinput.service", "voiceconductor.service"])

    def test_keeps_only_voiceinput(self):
        kept = names("voice.keep_mic=on\n")
        self.assertNotIn("voiceinput", kept)
        for name in STAYS_STUBBED:
            self.assertIn(name, kept)
        self.assertEqual(sh("voice_units", "voice.keep_mic=on\n").stdout.split(), ["voiceconductor.service"])

    def test_does_nothing_while_voice_is_off(self):
        conf = "voice.stop=off\nvoice.keep_mic=on\n"
        self.assertNotEqual(sh("voice_mic_kept", conf).returncode, 0)
        self.assertIn("voiceinput", names(conf))

    def test_is_a_known_setting(self):
        self.assertIn("voice.keep_mic", sh("conf_keys").stdout.split())

    def test_status_does_not_count_a_kept_voiceinput_as_a_fault(self):
        out = sh("group_targets voice", "voice.keep_mic=on\n").stdout
        self.assertNotIn("voiceinput /usr/sbin/voiceinput\n", out)


class ClaimTest(unittest.TestCase):
    CHECK = 'echo "$PID_TEXT" > "$T/claim.svc"; answer_claimed svc'

    def test_no_claim(self):
        self.assertNotEqual(sh("answer_claimed svc").returncode, 0)

    def test_live_pid(self):
        self.assertEqual(sh(self.CHECK.replace("$PID_TEXT", "$$")).returncode, 0)

    def test_dead_pid(self):
        self.assertNotEqual(sh(self.CHECK, PID_TEXT="999999999").returncode, 0)

    def test_junk(self):
        for text in ("", "self", "1;2", "../1"):
            self.assertNotEqual(sh(self.CHECK, PID_TEXT=text).returncode, 0, text)


if __name__ == "__main__":
    unittest.main()
