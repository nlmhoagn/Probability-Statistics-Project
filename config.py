"""
config.py
=========
Central Configuration and Experimental Design Definitions
MT2013 - Course Project (Class CC09)

Topic: Analysis of the Relationship between Password Length, Character Set Complexity,
       and Brute-force Cracking Time / Number of Attempts.
"""

import string
import platform
import sys
from datetime import datetime

# ==============================================================================
# 1. Character Set Complexity Levels (Axis 2)
# ==============================================================================
# Special character subset chosen according to OWASP / NIST SP 800-63B standards
SPECIAL_CHARS = "!@#$%^&*"
HEAVY_SEARCH_SPACE_THRESHOLD = 500_000

CHARSETS = {
    "digits": {
        "id": 1,
        "name": "Digits (0-9)",
        "chars": string.digits,
        "K": 10,
        "description": "Numeric digits only",
    },
    "lowercase": {
        "id": 2,
        "name": "Lowercase (a-z)",
        "chars": string.ascii_lowercase,
        "K": 26,
        "description": "Lowercase English letters",
    },
    "alphanumeric": {
        "id": 3,
        "name": "Alphanumeric (0-9, a-z, A-Z)",
        "chars": string.digits + string.ascii_lowercase + string.ascii_uppercase,
        "K": 62,
        "description": "Upper/lower letters and digits",
    },
    "full": {
        "id": 4,
        "name": "Full / Special (0-9, a-z, A-Z, !@#$%^&*)",
        "chars": string.digits + string.ascii_lowercase + string.ascii_uppercase + SPECIAL_CHARS,
        "K": 70,
        "description": "Full complexity including 8 common symbols",
    },
}

# ==============================================================================
# 2. Two-Factor Experimental Design Matrix
# ==============================================================================
# Axis 1: Length Effect on Full Complexity (K = 70 fixed, L in {1, 2, 3, 4})
AXIS_1_CONFIG = {
    "name": "Axis 1: Password Length Effect (Full Charset K=70)",
    "charset_key": "full",
    "lengths": [1, 2, 3, 4],
    "default_samples_per_group": 60,
}

# Axis 2: Charset Complexity Effect at Fixed Length (L = 4 fixed, K in {10, 26, 62, 70})
AXIS_2_CONFIG = {
    "name": "Axis 2: Charset Complexity Effect (Fixed Length L=4)",
    "fixed_length": 4,
    "charset_keys": ["digits", "lowercase", "alphanumeric", "full"],
    "default_samples_per_group": 60,
}

# ==============================================================================
# 3. Hardware & Environment Metadata (For Section 2.5 & Appendix C)
# ==============================================================================
def get_hardware_environment() -> dict:
    """Detect current system environment for scientific reproducibility."""
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "hash_algorithm": "SHA-256",
        "timer_function": "time.perf_counter_ns",
    }
