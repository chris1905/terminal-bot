"""Weather mood: fetch weather from wttr.in, map to bot mood."""

import urllib.request
import json
import ssl
import time

from buddy.ansi import strip_ansi

MOOD_MAP = {
    "clear": ("happy", "Clear skies! Perfect coding weather!"),
    "sunny": ("happy", "Sunny vibes for sunny code!"),
    "partly cloudy": ("neutral", "Cloudy outside, clear code inside."),
    "cloudy": ("neutral", "Overcast skies. Cozy coding time."),
    "overcast": ("neutral", "Grey skies, bright code."),
    "rain": ("cozy", "Rainy day coding? Peak vibes."),
    "light rain": ("cozy", "Light rain outside. Perfect ambiance."),
    "heavy rain": ("cozy", "Pouring rain! Stay in and code!"),
    "drizzle": ("cozy", "Drizzly day. Cozy terminal time."),
    "snow": ("excited", "Snow day! Let's build something cool!"),
    "thunderstorm": ("intense", "Thunder and code! ELECTRIC energy!"),
    "fog": ("mysterious", "Foggy out there... debugging weather."),
    "mist": ("mysterious", "Misty vibes. Mysterious code incoming."),
    "wind": ("energetic", "Windy! Blow through that backlog!"),
}

# Map moods to eye styles
MOOD_EYES = {
    "happy": "star",
    "neutral": "open",
    "cozy": "happy",
    "excited": "star",
    "intense": "open",
    "mysterious": "cool",
    "energetic": "open",
}


class WeatherMood:
    """Fetches weather and maps to bot mood."""

    def __init__(self):
        self.current = None   # {temp, condition, mood, message}
        self.last_fetch = 0
        self.fetch_interval = 1800  # 30 minutes

    def should_refresh(self):
        return time.time() - self.last_fetch > self.fetch_interval

    @staticmethod
    def _make_ssl_ctx():
        """Build an SSL context that verifies certificates."""
        for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
                       "/usr/local/etc/openssl/cert.pem"):
            try:
                return ssl.create_default_context(cafile=cafile)
            except Exception:
                continue
        return ssl.create_default_context()

    def fetch_weather(self):
        """Fetch from wttr.in. Safe to call from background thread."""
        try:
            req = urllib.request.Request(
                "https://wttr.in/?format=j1",
                headers={"User-Agent": "terminal-buddy/1.0"}
            )
            ssl_ctx = self._make_ssl_ctx()
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                raw = resp.read(1_048_576)  # Bound read to 1 MB
                data = json.loads(raw.decode("utf-8"))

            current = data.get("current_condition", [{}])[0]
            # Strip ANSI from external data at source
            condition = strip_ansi(current.get("weatherDesc", [{}])[0].get("value", "Unknown"))
            temp_c = strip_ansi(str(current.get("temp_C", "?")))
            temp_f = strip_ansi(str(current.get("temp_F", "?")))

            # Map condition to mood
            condition_lower = condition.lower()
            mood = "neutral"
            message = f"Weather: {condition}, {temp_c}C / {temp_f}F"
            for key, (m, msg) in MOOD_MAP.items():
                if key in condition_lower:
                    mood = m
                    message = f"{msg}\n({condition}, {temp_c}C / {temp_f}F)"
                    break

            self.current = {
                "condition": condition,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "mood": mood,
                "message": message,
            }
            self.last_fetch = time.time()
            return self.current

        except Exception:
            return None

    def get_mood(self):
        """Returns current mood string or None."""
        if self.current:
            return self.current["mood"]
        return None

    def get_eye_style(self):
        """Returns eye style override for current mood, or None."""
        mood = self.get_mood()
        if mood:
            return MOOD_EYES.get(mood)
        return None

    def get_message(self):
        """Returns weather message or None."""
        if self.current:
            return self.current["message"]
        return None
