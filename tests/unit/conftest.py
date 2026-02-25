"""Unit-test-specific fixtures. No live DB or API calls."""
import pytest
import json
import base64
from io import BytesIO
from PIL import Image


@pytest.fixture
def mock_claude_response_clean():
    """Claude API response returning clean JSON (no markdown wrapping)."""
    return json.dumps({
        "fp_category": "dress",
        "nickname": "gown",
        "silhouette": "a-line",
        "neckline": "v-neck",
        "waistline": "empire waistline",
        "length": "floor length",
        "sleeve_length": "sleeveless",
        "opening_type": None,
        "textile_pattern": "floral",
        "textile_finishing": ["pleated"],
        "garment_parts": ["collar", "sleeve"],
        "decorations": ["bow"],
        "era": "Victorian",
        "decade": "1870s",
        "style_tags": ["dark academia", "cottagecore", "romantic"],
        "colors": ["ivory", "dusty rose"],
        "material": "silk taffeta",
        "season": "spring/summer",
        "garment_type": "bustle day dress",
        "vibe": "romantic pastoral",
        "fit_style": "corseted fitted",
        "occasion": "garden party",
        "ai_description": (
            "A Victorian bustle day dress in ivory silk taffeta "
            "with dusty rose floral accents."
        ),
    })


@pytest.fixture
def mock_claude_response_markdown_wrapped(mock_claude_response_clean):
    """Claude response wrapped in ```json ... ``` markdown fences."""
    return f"```json\n{mock_claude_response_clean}\n```"


@pytest.fixture
def mock_claude_response_generic_fence(mock_claude_response_clean):
    """Claude response wrapped in ``` ... ``` (no language tag)."""
    return f"```\n{mock_claude_response_clean}\n```"


@pytest.fixture
def mock_claude_response_malformed():
    """Malformed JSON that should trigger fallback."""
    return '{"fp_category": "dress", "nickname": INVALID JSON HERE'


@pytest.fixture
def valid_data_url():
    """A minimal valid PNG data URL (1x1 red pixel)."""
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


@pytest.fixture
def invalid_data_url():
    """An invalid data URL that should return None from decode_data_url."""
    return "not-a-data-url"
