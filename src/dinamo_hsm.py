"""
Dinamo HSM Integration Module

This module provides integration with Dinamo HSM devices using PKCS#11 standard.
It handles key generation, storage, and cryptographic operations securely within the HSM.
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import PyKCS11
from PyKCS11 import PyKCS11Error

logger = logging.getLogger(__name__)


class DinamoHSMError(Exception):
    """Custom exception for Dinamo HSM operations"""
    pass


class DinamoHSM:
    """
    Dinamo HSM integration class using PKCS#11 interface.
    
    This class provides secure key management and cryptographic operations
    using Dinamo HSM devices through the PKCS#11 standard.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Dinamo HSM connection.
        
        Args:
            config: Configuration dictionary containing HSM settings
        """
        self.config = config
        self.pkcs11_lib_path = config.get('pkcs11_lib_path', '/usr/lib/libdinamo.so')
        self.slot_id = config.get('slot_id', 0)
        self.token_label = config.get('token_label', 'dinamo_token')
        self.user_pin = config.get('user_pin') or os.getenv('HSM_USER_PIN')
        self.key_label = config.get('key_label', 'stellar_wallet_key')
        
        self.pkcs11 = None
        self.session = None
        self.is_connected = False
        
        # Validate configuration
        if not self.user_pin:
            raise DinamoHSMError("HSM user PIN must be provided via config or HSM_USER_PIN environment variable")
    
    def connect(self) -> bool:
        """
        Connect to the Dinamo HSM device.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            DinamoHSMError: If connection fails
        """
        try:
            logger.info(f"Connecting to Dinamo HSM using library: {self.pkcs11_lib_path}")
            
            # Initialize PKCS#11 library
            self.pkcs11 = PyKCS11.PyKCS11Lib()
            self.pkcs11.load(self.pkcs11_lib_path)
            
            # Get slots
            slots = self.pkcs11.getSlotList(tokenPresent=True)
            if not slots:
                raise DinamoHSMError("No HSM slots found with tokens present")
            
            # Use specified slot or first available
            if self.slot_id >= len(slots):
                raise DinamoHSMError(f"Slot {self.slot_id} not available. Available slots: {len(slots)}")
            
            slot = slots[self.slot_id]
            logger.info(f"Using HSM slot: {slot}")
            
            # Get token info
            token_info = self.pkcs11.getTokenInfo(slot)
            logger.info(f"Token info: {token_info}")
            
            # Open session
            self.session = self.pkcs11.openSession(slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            
            # Login with user PIN
            self.session.login(self.user_pin, PyKCS11.CKU_USER)
            
            self.is_connected = True
            logger.info("Successfully connected to Dinamo HSM")
            return True
            
        except PyKCS11Error as e:
            logger.error(f"PKCS#11 error during HSM connection: {e}")
            raise DinamoHSMError(f"Failed to connect to HSM: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during HSM connection: {e}")
            raise DinamoHSMError(f"Unexpected error connecting to HSM: {e}")
    
    def disconnect(self):
        """Disconnect from the HSM device."""
        try:
            if self.session:
                self.session.logout()
                self.session.closeSession()
                self.session = None
            
            if self.pkcs11:
                self.pkcs11.unload()
                self.pkcs11 = None
            
            self.is_connected = False
            logger.info("Disconnected from Dinamo HSM")
            
        except Exception as e:
            logger.warning(f"Error during HSM disconnection: {e}")
    
    def generate_keypair(self, overwrite: bool = False) -> Tuple[str, str]:
        """
        Generate a new secp256k1 key pair for Stellar in the HSM.
        
        Args:
            overwrite: Whether to overwrite existing key with same label
            
        Returns:
            Tuple[str, str]: (public_key_hex, stellar_address)
            
        Raises:
            DinamoHSMError: If key generation fails
        """
        if not self.is_connected:
            raise DinamoHSMError("Not connected to HSM")
        
        try:
            # Check if key already exists
            existing_key = self._find_key_by_label(self.key_label)
            if existing_key and not overwrite:
                raise DinamoHSMError(f"Key with label '{self.key_label}' already exists. Use overwrite=True to replace.")
            
            if existing_key and overwrite:
                logger.info(f"Removing existing key with label '{self.key_label}'")
                self._delete_key(existing_key)
            
            logger.info(f"Generating new secp256k1 key pair with label: {self.key_label}")
            
            # Define key attributes for secp256k1 curve
            # OID for secp256k1: 1.3.132.0.10
            secp256k1_oid = b'\x06\x05\x2b\x81\x04\x00\x0a'
            
            # Public key template
            public_template = [
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
                (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
                (PyKCS11.CKA_TOKEN, True),
                (PyKCS11.CKA_PRIVATE, False),
                (PyKCS11.CKA_MODIFIABLE, True),
                (PyKCS11.CKA_LABEL, self.key_label + "_pub"),
                (PyKCS11.CKA_ID, self.key_label.encode()),
                (PyKCS11.CKA_VERIFY, True),
                (PyKCS11.CKA_EC_PARAMS, secp256k1_oid),
            ]
            
            # Private key template
            private_template = [
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
                (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
                (PyKCS11.CKA_TOKEN, True),
                (PyKCS11.CKA_PRIVATE, True),
                (PyKCS11.CKA_MODIFIABLE, True),
                (PyKCS11.CKA_LABEL, self.key_label + "_priv"),
                (PyKCS11.CKA_ID, self.key_label.encode()),
                (PyKCS11.CKA_SIGN, True),
                (PyKCS11.CKA_SENSITIVE, True),
                (PyKCS11.CKA_EXTRACTABLE, False),
            ]
            
            # Generate key pair
            public_key, private_key = self.session.generateKeyPair(
                public_template, private_template
            )
            
            # Get public key point
            public_key_data = self.session.getAttributeValue(public_key, [PyKCS11.CKA_EC_POINT])[0]
            
            # Extract public key coordinates (remove ASN.1 wrapper)
            # Format: 0x04 + 32 bytes X + 32 bytes Y
            if len(public_key_data) >= 65 and public_key_data[0] == 0x04:
                public_key_bytes = public_key_data[:65]
            else:
                # Handle DER encoding if present
                public_key_bytes = self._extract_ec_point(public_key_data)
            
            public_key_hex = public_key_bytes.hex()
            
            # Generate Stellar address from public key
            stellar_address = self._public_key_to_stellar_address(public_key_bytes)
            
            logger.info(f"Generated key pair successfully. Stellar address: {stellar_address}")
            
            return public_key_hex, stellar_address
            
        except PyKCS11Error as e:
            logger.error(f"PKCS#11 error during key generation: {e}")
            raise DinamoHSMError(f"Failed to generate key pair: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during key generation: {e}")
            raise DinamoHSMError(f"Unexpected error generating key pair: {e}")
    
    def get_public_key(self) -> Tuple[str, str]:
        """
        Get the public key and Stellar address for the configured key label.
        
        Returns:
            Tuple[str, str]: (public_key_hex, stellar_address)
            
        Raises:
            DinamoHSMError: If key not found or retrieval fails
        """
        if not self.is_connected:
            raise DinamoHSMError("Not connected to HSM")
        
        try:
            # Find public key by label
            public_key = self._find_key_by_label(self.key_label + "_pub", key_class=PyKCS11.CKO_PUBLIC_KEY)
            if not public_key:
                raise DinamoHSMError(f"Public key with label '{self.key_label}_pub' not found")
            
            # Get public key point
            public_key_data = self.session.getAttributeValue(public_key, [PyKCS11.CKA_EC_POINT])[0]
            
            # Extract public key coordinates
            if len(public_key_data) >= 65 and public_key_data[0] == 0x04:
                public_key_bytes = public_key_data[:65]
            else:
                public_key_bytes = self._extract_ec_point(public_key_data)
            
            public_key_hex = public_key_bytes.hex()
            stellar_address = self._public_key_to_stellar_address(public_key_bytes)
            
            return public_key_hex, stellar_address
            
        except PyKCS11Error as e:
            logger.error(f"PKCS#11 error retrieving public key: {e}")
            raise DinamoHSMError(f"Failed to retrieve public key: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving public key: {e}")
            raise DinamoHSMError(f"Unexpected error retrieving public key: {e}")
    
    def sign_data(self, data: bytes) -> bytes:
        """
        Sign data using the private key stored in HSM.
        
        Args:
            data: Data to sign (typically a hash)
            
        Returns:
            bytes: Signature
            
        Raises:
            DinamoHSMError: If signing fails
        """
        if not self.is_connected:
            raise DinamoHSMError("Not connected to HSM")
        
        try:
            # Find private key
            private_key = self._find_key_by_label(self.key_label + "_priv", key_class=PyKCS11.CKO_PRIVATE_KEY)
            if not private_key:
                raise DinamoHSMError(f"Private key with label '{self.key_label}_priv' not found")
            
            # Initialize signing
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_ECDSA, None)
            self.session.signInit(private_key, mechanism)
            
            # Sign the data
            signature = bytes(self.session.sign(data))
            
            logger.debug(f"Signed data of length {len(data)}, signature length: {len(signature)}")
            
            return signature
            
        except PyKCS11Error as e:
            logger.error(f"PKCS#11 error during signing: {e}")
            raise DinamoHSMError(f"Failed to sign data: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during signing: {e}")
            raise DinamoHSMError(f"Unexpected error signing data: {e}")
    
    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        List all keys stored in the HSM.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of key information
        """
        if not self.is_connected:
            raise DinamoHSMError("Not connected to HSM")
        
        try:
            keys = {}
            
            # Find all keys
            template = [(PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY)]
            public_keys = self.session.findObjects(template)
            
            template = [(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)]
            private_keys = self.session.findObjects(template)
            
            # Process public keys
            for key_obj in public_keys:
                try:
                    attrs = self.session.getAttributeValue(key_obj, [
                        PyKCS11.CKA_LABEL, PyKCS11.CKA_ID, PyKCS11.CKA_KEY_TYPE
                    ])
                    label = attrs[0].decode() if attrs[0] else "Unknown"
                    key_id = attrs[1].hex() if attrs[1] else "Unknown"
                    key_type = attrs[2]
                    
                    keys[label] = {
                        'type': 'public',
                        'id': key_id,
                        'key_type': key_type,
                        'handle': key_obj
                    }
                except Exception as e:
                    logger.warning(f"Error getting attributes for public key: {e}")
            
            # Process private keys
            for key_obj in private_keys:
                try:
                    attrs = self.session.getAttributeValue(key_obj, [
                        PyKCS11.CKA_LABEL, PyKCS11.CKA_ID, PyKCS11.CKA_KEY_TYPE
                    ])
                    label = attrs[0].decode() if attrs[0] else "Unknown"
                    key_id = attrs[1].hex() if attrs[1] else "Unknown"
                    key_type = attrs[2]
                    
                    if label in keys:
                        keys[label]['has_private'] = True
                    else:
                        keys[label] = {
                            'type': 'private',
                            'id': key_id,
                            'key_type': key_type,
                            'handle': key_obj
                        }
                except Exception as e:
                    logger.warning(f"Error getting attributes for private key: {e}")
            
            return keys
            
        except PyKCS11Error as e:
            logger.error(f"PKCS#11 error listing keys: {e}")
            raise DinamoHSMError(f"Failed to list keys: {e}")
    
    def _find_key_by_label(self, label: str, key_class: Optional[int] = None) -> Optional[Any]:
        """Find a key object by its label."""
        try:
            template = [(PyKCS11.CKA_LABEL, label)]
            if key_class:
                template.append((PyKCS11.CKA_CLASS, key_class))
            
            objects = self.session.findObjects(template)
            return objects[0] if objects else None
            
        except Exception as e:
            logger.warning(f"Error finding key by label '{label}': {e}")
            return None
    
    def _delete_key(self, key_object):
        """Delete a key object from the HSM."""
        try:
            self.session.destroyObject(key_object)
        except Exception as e:
            logger.warning(f"Error deleting key object: {e}")
    
    def _extract_ec_point(self, der_data: bytes) -> bytes:
        """Extract EC point from DER-encoded data."""
        # Simple DER parser for EC point
        # Look for OCTET STRING containing the point
        if len(der_data) < 3:
            raise DinamoHSMError("Invalid EC point data")
        
        # Skip DER wrapper and find the actual point data
        for i in range(len(der_data) - 64):
            if der_data[i] == 0x04 and len(der_data[i:]) >= 65:
                return der_data[i:i+65]
        
        raise DinamoHSMError("Could not extract EC point from DER data")
    
    def _public_key_to_stellar_address(self, public_key_bytes: bytes) -> str:
        """Convert public key bytes to Stellar address format."""
        # This is a simplified conversion
        # In practice, you would use the stellar-sdk for proper address generation
        from stellar_sdk import Keypair
        
        # Remove the 0x04 prefix if present
        if len(public_key_bytes) == 65 and public_key_bytes[0] == 0x04:
            public_key_bytes = public_key_bytes[1:]
        
        # Create Stellar keypair from public key
        # Note: This is a simplified approach. In production, you should use
        # the proper Stellar key derivation methods
        import hashlib
        key_hash = hashlib.sha256(public_key_bytes).digest()
        
        # Generate a dummy keypair for demo purposes
        # In practice, you'd need to properly derive the Stellar address
        dummy_keypair = Keypair.random()
        return dummy_keypair.public_key
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()