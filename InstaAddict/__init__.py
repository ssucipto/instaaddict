"""InstaAddict - Human-like Instagram bot powered by UIAutomator2"""

__version__ = "1.2.1"
__tested_ig_version__ = "446.0.0.0.0"

from InstaAddict.core.bot_flow import start_bot


def run(**kwargs):
    start_bot(**kwargs)
