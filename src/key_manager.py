"""
HSM-Secured Key Management System

This module provides advanced key management capabilities for the Stellar wallet,
including key lifecycle management, backup procedures, and security policies.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from .dinamo_hsm import DinamoHSM, DinamoHSMError

logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    """Key status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPROMISED = "compromised"
    EXPIRED = "expired"
    PENDING_DELETION = "pending_deletion"


class KeyType(Enum):
    """Key type enumeration"""
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    MASTER = "master"


@dataclass
class KeyMetadata:
    """Key metadata structure"""
    key_id: str
    label: str
    key_type: KeyType
    status: KeyStatus
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_count: int = 0
    backup_status: str = "none"
    description: Optional[str] = None


class KeyManagerError(Exception):
    """Custom exception for key manager operations"""
    pass


class KeyManager:
    """
    Advanced key management system for HSM-secured Stellar wallet.
    
    Features:
    - Key lifecycle management
    - Usage tracking and auditing
    - Key rotation and backup
    - Security policy enforcement
    - Compliance reporting
    """
    
    def __init__(self, config: Dict[str, Any], hsm: DinamoHSM):
        """
        Initialize the key manager.
        
        Args:
            config: Configuration dictionary
            hsm: DinamoHSM instance
        """
        self.config = config
        self.hsm = hsm
        self.security_config = config.get('security', {})
        
        # Key management settings
        self.require_confirmation = self.security_config.get('require_user_confirmation', True)
        self.audit_logging = self.security_config.get('audit_logging', True)
        self.key_backup_required = self.security_config.get('key_backup_required', False)
        
        # Key metadata storage (in production, use a secure database)
        self.metadata_file = config.get('metadata_file', 'key_metadata.json')
        self.key_metadata: Dict[str, KeyMetadata] = {}
        
        # Load existing metadata
        self._load_metadata()
        
        logger.info("Key manager initialized")
    
    def create_stellar_key(self, 
                          key_label: str,
                          description: Optional[str] = None,
                          expires_days: Optional[int] = None) -> Tuple[str, str]:
        """
        Create a new Stellar signing key in the HSM.
        
        Args:
            key_label: Label for the key
            description: Key description
            expires_days: Days until key expires (optional)
            
        Returns:
            Tuple[str, str]: (public_key_hex, stellar_address)
            
        Raises:
            KeyManagerError: If key creation fails
        """
        try:
            logger.info(f"Creating new Stellar key: {key_label}")
            
            # Check if key already exists
            if key_label in self.key_metadata:
                raise KeyManagerError(f"Key with label '{key_label}' already exists")
            
            # User confirmation if required
            if self.require_confirmation:
                if not self._get_user_confirmation(f"Create new key '{key_label}'?"):
                    raise KeyManagerError("Key creation cancelled by user")
            
            # Create key in HSM
            if not self.hsm.is_connected:
                self.hsm.connect()
            
            # Temporarily update HSM key label for creation
            original_label = self.hsm.key_label
            self.hsm.key_label = key_label
            
            try:
                public_key_hex, stellar_address = self.hsm.generate_keypair(overwrite=False)
            finally:
                # Restore original label
                self.hsm.key_label = original_label
            
            # Create metadata
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            metadata = KeyMetadata(
                key_id=hashlib.sha256(key_label.encode()).hexdigest()[:16],
                label=key_label,
                key_type=KeyType.SIGNING,
                status=KeyStatus.ACTIVE,
                created_at=datetime.now(),
                expires_at=expires_at,
                description=description
            )
            
            self.key_metadata[key_label] = metadata
            self._save_metadata()
            
            # Audit log
            if self.audit_logging:
                self._audit_log("KEY_CREATED", {
                    "key_label": key_label,
                    "stellar_address": stellar_address,
                    "key_type": "signing",
                    "expires_at": expires_at.isoformat() if expires_at else None
                })
            
            logger.info(f"Key '{key_label}' created successfully. Address: {stellar_address}")
            
            return public_key_hex, stellar_address
            
        except DinamoHSMError as e:
            logger.error(f"HSM error creating key: {e}")
            raise KeyManagerError(f"Failed to create key: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating key: {e}")
            raise KeyManagerError(f"Unexpected error creating key: {e}")
    
    def get_key_info(self, key_label: str) -> Dict[str, Any]:
        """
        Get information about a specific key.
        
        Args:
            key_label: Key label
            
        Returns:
            Dict[str, Any]: Key information
            
        Raises:
            KeyManagerError: If key not found
        """
        if key_label not in self.key_metadata:
            raise KeyManagerError(f"Key '{key_label}' not found")
        
        metadata = self.key_metadata[key_label]
        
        # Check if key is expired
        if metadata.expires_at and datetime.now() > metadata.expires_at:
            if metadata.status == KeyStatus.ACTIVE:
                metadata.status = KeyStatus.EXPIRED
                self._save_metadata()
        
        key_info = asdict(metadata)
        
        # Add HSM status if connected
        try:
            if self.hsm.is_connected:
                hsm_keys = self.hsm.list_keys()
                key_info['hsm_present'] = any(key_label in k for k in hsm_keys.keys())
            else:
                key_info['hsm_present'] = None
        except Exception as e:
            logger.warning(f"Error checking HSM key status: {e}")
            key_info['hsm_present'] = None
        
        return key_info
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """
        List all managed keys.
        
        Returns:
            List[Dict[str, Any]]: List of key information
        """
        keys = []
        for label, metadata in self.key_metadata.items():
            try:
                key_info = self.get_key_info(label)
                keys.append(key_info)
            except Exception as e:
                logger.warning(f"Error getting info for key '{label}': {e}")
        
        return keys
    
    def use_key(self, key_label: str, operation: str) -> bool:
        """
        Record key usage and perform security checks.
        
        Args:
            key_label: Key label
            operation: Operation being performed
            
        Returns:
            bool: True if key usage is allowed
            
        Raises:
            KeyManagerError: If key usage is not allowed
        """
        if key_label not in self.key_metadata:
            raise KeyManagerError(f"Key '{key_label}' not found")
        
        metadata = self.key_metadata[key_label]
        
        # Check key status
        if metadata.status != KeyStatus.ACTIVE:
            raise KeyManagerError(f"Key '{key_label}' is not active (status: {metadata.status.value})")
        
        # Check expiration
        if metadata.expires_at and datetime.now() > metadata.expires_at:
            metadata.status = KeyStatus.EXPIRED
            self._save_metadata()
            raise KeyManagerError(f"Key '{key_label}' has expired")
        
        # Update usage statistics
        metadata.usage_count += 1
        metadata.last_used = datetime.now()
        self._save_metadata()
        
        # Audit log
        if self.audit_logging:
            self._audit_log("KEY_USED", {
                "key_label": key_label,
                "operation": operation,
                "usage_count": metadata.usage_count
            })
        
        return True
    
    def deactivate_key(self, key_label: str, reason: str = "Manual deactivation") -> bool:
        """
        Deactivate a key.
        
        Args:
            key_label: Key label
            reason: Reason for deactivation
            
        Returns:
            bool: True if successful
            
        Raises:
            KeyManagerError: If deactivation fails
        """
        if key_label not in self.key_metadata:
            raise KeyManagerError(f"Key '{key_label}' not found")
        
        # User confirmation if required
        if self.require_confirmation:
            if not self._get_user_confirmation(f"Deactivate key '{key_label}'?"):
                raise KeyManagerError("Key deactivation cancelled by user")
        
        metadata = self.key_metadata[key_label]
        metadata.status = KeyStatus.INACTIVE
        self._save_metadata()
        
        # Audit log
        if self.audit_logging:
            self._audit_log("KEY_DEACTIVATED", {
                "key_label": key_label,
                "reason": reason
            })
        
        logger.info(f"Key '{key_label}' deactivated: {reason}")
        return True
    
    def mark_compromised(self, key_label: str, incident_id: Optional[str] = None) -> bool:
        """
        Mark a key as compromised.
        
        Args:
            key_label: Key label
            incident_id: Security incident ID
            
        Returns:
            bool: True if successful
            
        Raises:
            KeyManagerError: If operation fails
        """
        if key_label not in self.key_metadata:
            raise KeyManagerError(f"Key '{key_label}' not found")
        
        metadata = self.key_metadata[key_label]
        metadata.status = KeyStatus.COMPROMISED
        self._save_metadata()
        
        # Audit log
        if self.audit_logging:
            self._audit_log("KEY_COMPROMISED", {
                "key_label": key_label,
                "incident_id": incident_id,
                "immediate_action_required": True
            })
        
        logger.critical(f"Key '{key_label}' marked as compromised. Incident ID: {incident_id}")
        return True
    
    def rotate_key(self, old_key_label: str, new_key_label: str) -> Tuple[str, str]:
        """
        Rotate a key by creating a new one and deactivating the old one.
        
        Args:
            old_key_label: Label of the key to rotate
            new_key_label: Label for the new key
            
        Returns:
            Tuple[str, str]: (public_key_hex, stellar_address) of new key
            
        Raises:
            KeyManagerError: If rotation fails
        """
        try:
            logger.info(f"Rotating key from '{old_key_label}' to '{new_key_label}'")
            
            # User confirmation if required
            if self.require_confirmation:
                if not self._get_user_confirmation(f"Rotate key '{old_key_label}' to '{new_key_label}'?"):
                    raise KeyManagerError("Key rotation cancelled by user")
            
            # Create new key
            public_key_hex, stellar_address = self.create_stellar_key(
                new_key_label,
                description=f"Rotated from {old_key_label}"
            )
            
            # Deactivate old key
            self.deactivate_key(old_key_label, f"Rotated to {new_key_label}")
            
            # Audit log
            if self.audit_logging:
                self._audit_log("KEY_ROTATED", {
                    "old_key_label": old_key_label,
                    "new_key_label": new_key_label,
                    "new_stellar_address": stellar_address
                })
            
            logger.info(f"Key rotation completed successfully")
            return public_key_hex, stellar_address
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise KeyManagerError(f"Key rotation failed: {e}")
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        Generate a security report for all keys.
        
        Returns:
            Dict[str, Any]: Security report
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_keys": len(self.key_metadata),
            "key_status_summary": {},
            "expiring_keys": [],
            "high_usage_keys": [],
            "inactive_keys": [],
            "security_issues": []
        }
        
        # Count keys by status
        for metadata in self.key_metadata.values():
            status = metadata.status.value
            report["key_status_summary"][status] = report["key_status_summary"].get(status, 0) + 1
        
        # Check for expiring keys (within 30 days)
        expiry_threshold = datetime.now() + timedelta(days=30)
        for label, metadata in self.key_metadata.items():
            if metadata.expires_at and metadata.expires_at <= expiry_threshold:
                report["expiring_keys"].append({
                    "label": label,
                    "expires_at": metadata.expires_at.isoformat(),
                    "days_remaining": (metadata.expires_at - datetime.now()).days
                })
        
        # Check for high usage keys (> 1000 uses)
        for label, metadata in self.key_metadata.items():
            if metadata.usage_count > 1000:
                report["high_usage_keys"].append({
                    "label": label,
                    "usage_count": metadata.usage_count,
                    "last_used": metadata.last_used.isoformat() if metadata.last_used else None
                })
        
        # Check for inactive keys
        inactive_threshold = datetime.now() - timedelta(days=90)
        for label, metadata in self.key_metadata.items():
            if (metadata.last_used and metadata.last_used < inactive_threshold) or \
               (not metadata.last_used and metadata.created_at < inactive_threshold):
                report["inactive_keys"].append({
                    "label": label,
                    "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
                    "created_at": metadata.created_at.isoformat()
                })
        
        # Check for security issues
        for label, metadata in self.key_metadata.items():
            if metadata.status == KeyStatus.COMPROMISED:
                report["security_issues"].append({
                    "type": "compromised_key",
                    "key_label": label,
                    "severity": "critical"
                })
            elif metadata.status == KeyStatus.EXPIRED:
                report["security_issues"].append({
                    "type": "expired_key",
                    "key_label": label,
                    "severity": "high"
                })
        
        return report
    
    def backup_key_metadata(self, backup_path: str) -> bool:
        """
        Backup key metadata to a secure location.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            bool: True if successful
        """
        try:
            # Prepare backup data
            backup_data = {
                "backup_created_at": datetime.now().isoformat(),
                "version": "1.0",
                "key_metadata": {}
            }
            
            # Convert metadata to serializable format
            for label, metadata in self.key_metadata.items():
                backup_data["key_metadata"][label] = {
                    **asdict(metadata),
                    "created_at": metadata.created_at.isoformat(),
                    "last_used": metadata.last_used.isoformat() if metadata.last_used else None,
                    "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
                    "status": metadata.status.value,
                    "key_type": metadata.key_type.value
                }
            
            # Write backup file
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Audit log
            if self.audit_logging:
                self._audit_log("METADATA_BACKUP", {
                    "backup_path": backup_path,
                    "keys_backed_up": len(self.key_metadata)
                })
            
            logger.info(f"Key metadata backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up key metadata: {e}")
            return False
    
    def _load_metadata(self):
        """Load key metadata from file."""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                for label, meta_dict in data.items():
                    # Convert string dates back to datetime objects
                    meta_dict['created_at'] = datetime.fromisoformat(meta_dict['created_at'])
                    if meta_dict.get('last_used'):
                        meta_dict['last_used'] = datetime.fromisoformat(meta_dict['last_used'])
                    if meta_dict.get('expires_at'):
                        meta_dict['expires_at'] = datetime.fromisoformat(meta_dict['expires_at'])
                    
                    # Convert string enums back to enum objects
                    meta_dict['status'] = KeyStatus(meta_dict['status'])
                    meta_dict['key_type'] = KeyType(meta_dict['key_type'])
                    
                    self.key_metadata[label] = KeyMetadata(**meta_dict)
                
                logger.info(f"Loaded metadata for {len(self.key_metadata)} keys")
        except Exception as e:
            logger.warning(f"Could not load key metadata: {e}")
    
    def _save_metadata(self):
        """Save key metadata to file."""
        try:
            # Convert to serializable format
            data = {}
            for label, metadata in self.key_metadata.items():
                meta_dict = asdict(metadata)
                meta_dict['created_at'] = metadata.created_at.isoformat()
                meta_dict['last_used'] = metadata.last_used.isoformat() if metadata.last_used else None
                meta_dict['expires_at'] = metadata.expires_at.isoformat() if metadata.expires_at else None
                meta_dict['status'] = metadata.status.value
                meta_dict['key_type'] = metadata.key_type.value
                data[label] = meta_dict
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving key metadata: {e}")
    
    def _get_user_confirmation(self, message: str) -> bool:
        """Get user confirmation for sensitive operations."""
        try:
            response = input(f"{message} (y/N): ").strip().lower()
            return response in ['y', 'yes']
        except:
            return False
    
    def _audit_log(self, event_type: str, details: Dict[str, Any]):
        """Log security events for auditing."""
        if not self.audit_logging:
            return
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "user": os.getenv("USER", "unknown")
        }
        
        # In production, this should go to a secure audit logging system
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    def close(self):
        """Clean up resources."""
        try:
            self._save_metadata()
            logger.info("Key manager closed successfully")
        except Exception as e:
            logger.warning(f"Error closing key manager: {e}")