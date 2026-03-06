#!/usr/bin/env python3
"""
ORDL Multi-Factor Authentication System
TOTP (RFC 6238) + Hardware Token Support
Classification: TOP SECRET//NOFORN//SCI
"""

import hashlib
import hmac
import base64
import struct
import time
import secrets
import qrcode
import io
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json


class MFAType(Enum):
    """MFA factor types"""
    TOTP = "totp"                    # Time-based OTP (Google Authenticator)
    HOTP = "hotp"                    # Counter-based OTP
    HARDWARE_TOKEN = "hardware"      # Physical token (YubiKey)
    SMART_CARD = "smartcard"         # CAC/PIV card
    BIOMETRIC_FINGERPRINT = "bio_fp" # Fingerprint
    BIOMETRIC_IRIS = "bio_iris"      # Iris scan
    VOICE_PRINT = "voice"            # Voice recognition
    PUSH_NOTIFICATION = "push"       # Mobile push
    BACKUP_CODES = "backup"          # Single-use backup codes


@dataclass
class MFADevice:
    """MFA device configuration"""
    device_id: str
    user_codename: str
    factor_type: str
    name: str
    created_at: str
    last_used: Optional[str] = None
    is_active: bool = True
    is_primary: bool = False
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'user_codename': self.user_codename,
            'factor_type': self.factor_type,
            'name': self.name,
            'created_at': self.created_at,
            'last_used': self.last_used,
            'is_active': self.is_active,
            'is_primary': self.is_primary,
            'metadata': self.metadata or {}
        }


class TOTPGenerator:
    """
    RFC 6238 TOTP Implementation
    Compatible with Google Authenticator, Authy, etc.
    """
    
    def __init__(self, secret: bytes = None, digits: int = 6, interval: int = 30):
        """
        Args:
            secret: Base32-encoded secret key
            digits: Number of digits in OTP (default 6)
            interval: Time step in seconds (default 30)
        """
        self.secret = secret or self.generate_secret()
        self.digits = digits
        self.interval = interval
    
    @staticmethod
    def generate_secret() -> bytes:
        """Generate random base32 secret"""
        # 160 bits = 32 base32 characters
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode('utf-8')
    
    def generate(self, timestamp: Optional[int] = None) -> str:
        """Generate TOTP for given timestamp (or current time)"""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Calculate time counter
        counter = struct.pack('>Q', timestamp // self.interval)
        
        # Decode base32 secret
        secret_bytes = base64.b32decode(self.secret.upper())
        
        # HMAC-SHA1
        mac = hmac.new(secret_bytes, counter, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = mac[-1] & 0x0f
        code = struct.unpack('>I', mac[offset:offset+4])[0]
        code = code & 0x7fffffff
        
        # Modulo to get required digits
        otp = code % (10 ** self.digits)
        
        return str(otp).zfill(self.digits)
    
    def verify(self, code: str, window: int = 1) -> bool:
        """
        Verify TOTP code with time window
        
        Args:
            code: The code to verify
            window: Number of intervals before/after current to accept
        
        Returns:
            True if code is valid
        """
        current_time = int(time.time())
        
        for offset in range(-window, window + 1):
            check_time = current_time + (offset * self.interval)
            expected = self.generate(check_time)
            
            # Constant-time comparison
            if hmac.compare_digest(code, expected):
                return True
        
        return False
    
    def get_uri(self, user: str, issuer: str = "ORDL") -> str:
        """
        Generate otpauth URI for QR code
        
        Format: otpauth://totp/ORDL:user?secret=XXX&issuer=ORDL
        """
        label = f"{issuer}:{user}"
        params = f"secret={self.secret}&issuer={issuer}&digits={self.digits}&period={self.interval}"
        return f"otpauth://totp/{label}?{params}"
    
    def generate_qr(self, user: str, issuer: str = "ORDL") -> bytes:
        """Generate QR code PNG bytes"""
        uri = self.get_uri(user, issuer)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'secret': self.secret,
            'digits': self.digits,
            'interval': self.interval
        }


class MFAManager:
    """
    Multi-Factor Authentication Manager
    Handles multiple factor types and enrollment
    """
    
    def __init__(self, storage_path: str = "/opt/codex-swarm/command-post/data/mfa.json"):
        self.storage_path = storage_path
        self._devices: Dict[str, MFADevice] = {}
        self._totp_secrets: Dict[str, TOTPGenerator] = {}
        self._backup_codes: Dict[str, set] = {}
        self._load_data()
    
    def _load_data(self):
        """Load MFA data from storage"""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for device_data in data.get('devices', []):
                    device = MFADevice(**device_data)
                    self._devices[device.device_id] = device
                    
                    # Load TOTP secrets
                    if device.factor_type == MFAType.TOTP.value:
                        if device.user_codename in data.get('totp_secrets', {}):
                            secret_data = data['totp_secrets'][device.user_codename]
                            self._totp_secrets[device.user_codename] = TOTPGenerator(**secret_data)
                    
                    # Load backup codes
                    if device.user_codename in data.get('backup_codes', {}):
                        self._backup_codes[device.user_codename] = set(
                            data['backup_codes'][device.user_codename]
                        )
        except FileNotFoundError:
            pass
    
    def _save_data(self):
        """Save MFA data to storage"""
        data = {
            'devices': [d.to_dict() for d in self._devices.values()],
            'totp_secrets': {
                user: gen.to_dict() 
                for user, gen in self._totp_secrets.items()
            },
            'backup_codes': {
                user: list(codes)
                for user, codes in self._backup_codes.items()
            }
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def enroll_totp(self, user_codename: str, device_name: str = "Authenticator") -> Dict[str, Any]:
        """
        Enroll TOTP for user
        
        Returns:
            Dict with secret and QR code bytes
        """
        # Generate new TOTP
        totp = TOTPGenerator()
        self._totp_secrets[user_codename] = totp
        
        # Create device record
        device = MFADevice(
            device_id=secrets.token_hex(16),
            user_codename=user_codename,
            factor_type=MFAType.TOTP.value,
            name=device_name,
            created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            is_primary=True
        )
        self._devices[device.device_id] = device
        
        # Generate backup codes
        backup_codes = self._generate_backup_codes(user_codename)
        
        self._save_data()
        
        # Generate QR code
        qr_bytes = totp.generate_qr(user_codename, "ORDL")
        
        return {
            'device': device.to_dict(),
            'secret': totp.secret,
            'qr_code_png': base64.b64encode(qr_bytes).decode(),
            'backup_codes': list(backup_codes),
            'uri': totp.get_uri(user_codename, "ORDL")
        }
    
    def _generate_backup_codes(self, user_codename: str, count: int = 10) -> set:
        """Generate single-use backup codes"""
        codes = set()
        for _ in range(count):
            # 8-digit codes
            code = ''.join(secrets.choice('0123456789') for _ in range(8))
            codes.add(code)
        
        self._backup_codes[user_codename] = codes
        return codes
    
    def verify_totp(self, user_codename: str, code: str) -> bool:
        """Verify TOTP code for user"""
        if user_codename not in self._totp_secrets:
            return False
        
        totp = self._totp_secrets[user_codename]
        if totp.verify(code):
            self._update_last_used(user_codename, MFAType.TOTP.value)
            return True
        
        return False
    
    def verify_backup_code(self, user_codename: str, code: str) -> bool:
        """Verify and consume backup code"""
        if user_codename not in self._backup_codes:
            return False
        
        codes = self._backup_codes[user_codename]
        if code in codes:
            codes.remove(code)  # Consume the code
            self._save_data()
            self._update_last_used(user_codename, MFAType.BACKUP_CODES.value)
            return True
        
        return False
    
    def _update_last_used(self, user_codename: str, factor_type: str):
        """Update last used timestamp"""
        for device in self._devices.values():
            if device.user_codename == user_codename and device.factor_type == factor_type:
                device.last_used = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        self._save_data()
    
    def get_user_devices(self, user_codename: str) -> list:
        """Get all MFA devices for user"""
        return [
            d.to_dict() for d in self._devices.values()
            if d.user_codename == user_codename and d.is_active
        ]
    
    def require_mfa(self, user_clearance: str) -> bool:
        """
        Determine if MFA is required based on clearance
        
        Returns True for SECRET and above
        """
        required_levels = ['SECRET', 'TOP SECRET', 'TS/SCI', 'TS/SCI/NOFORN']
        return user_clearance in required_levels
    
    def get_required_factors(self, user_clearance: str) -> int:
        """
        Get number of MFA factors required
        
        UNCLASSIFIED: 0
        CONFIDENTIAL: 0 (optional)
        SECRET: 1
        TOP SECRET: 1
        TS/SCI: 2
        TS/SCI/NOFORN: 2
        """
        mapping = {
            'UNCLASSIFIED': 0,
            'CONFIDENTIAL': 0,
            'SECRET': 1,
            'TOP SECRET': 1,
            'TS/SCI': 2,
            'TS/SCI/NOFORN': 2
        }
        return mapping.get(user_clearance, 1)


# Global MFA manager
_mfa_manager = None

def get_mfa_manager() -> MFAManager:
    """Get global MFA manager singleton"""
    global _mfa_manager
    if _mfa_manager is None:
        _mfa_manager = MFAManager()
    return _mfa_manager
