#!/usr/bin/env python3
"""
Advanced Features Example for Stellar Wallet with Dinamo HSM

This example demonstrates advanced features including:
1. Multi-signature account setup
2. Asset operations (trustlines, custom assets)
3. Key rotation procedures
4. Compliance and audit features
5. Advanced transaction types
"""

import os
import sys
import yaml
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.stellar_wallet import StellarWallet, StellarWalletError
from src.key_manager import KeyManager, KeyManagerError, KeyStatus
from loguru import logger
from stellar_sdk import Keypair, Asset

def setup_logging():
    """Set up logging configuration."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )

def load_config():
    """Load configuration from file and environment variables."""
    load_dotenv()
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables
    if os.getenv('HSM_USER_PIN'):
        config['hsm']['user_pin'] = os.getenv('HSM_USER_PIN')
    
    return config

def demo_multisig_setup():
    """Demonstrate multi-signature account setup."""
    logger.info("=== Multi-Signature Account Setup Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            wallet.initialize_wallet()
            
            # Create additional signers (for demo, we'll use random keypairs)
            signer1 = Keypair.random()
            signer2 = Keypair.random()
            
            logger.info(f"Primary wallet address: {wallet.get_stellar_address()}")
            logger.info(f"Additional signer 1: {signer1.public_key}")
            logger.info(f"Additional signer 2: {signer2.public_key}")
            
            # Note: In a real implementation, you would:
            # 1. Set the account thresholds
            # 2. Add additional signers
            # 3. Configure signing policies
            
            logger.info("Multi-sig setup would involve:")
            logger.info("1. Setting account thresholds for operations")
            logger.info("2. Adding additional signers to the account")
            logger.info("3. Configuring signing policies in HSM")
            logger.info("4. Testing multi-sig transaction flows")
            
    except Exception as e:
        logger.error(f"Multi-sig demo failed: {e}")
        return False
    
    logger.info("Multi-sig demo completed!")
    return True

def demo_asset_operations():
    """Demonstrate custom asset operations."""
    logger.info("=== Asset Operations Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            wallet.initialize_wallet()
            
            # Example custom asset
            asset_code = "DEMO"
            asset_issuer = "GCDNJUBQSX7AJWLJACMJ7I4BC3Z47BQUTMHEICZLE6MU4KQBRYG5JY6B"  # Example issuer
            
            logger.info(f"Working with custom asset: {asset_code}")
            logger.info(f"Asset issuer: {asset_issuer}")
            
            # In a real implementation, you would:
            # 1. Create trustline to the asset
            # 2. Receive/send the custom asset
            # 3. Manage asset balances
            
            logger.info("Asset operations would include:")
            logger.info("1. Creating trustlines to custom assets")
            logger.info("2. Managing asset balances")
            logger.info("3. Sending/receiving custom assets")
            logger.info("4. Setting asset authorization flags")
            
            # Check current balances
            try:
                account_info = wallet.get_account_info()
                logger.info("Current asset balances:")
                for balance in account_info['balances']:
                    if balance['asset_type'] == 'native':
                        logger.info(f"  XLM: {balance['balance']}")
                    else:
                        asset_code = balance.get('asset_code', 'Unknown')
                        asset_issuer = balance.get('asset_issuer', 'Unknown')
                        logger.info(f"  {asset_code}: {balance['balance']} (Issuer: {asset_issuer[:8]}...)")
            except Exception as e:
                logger.warning(f"Could not fetch balances: {e}")
            
    except Exception as e:
        logger.error(f"Asset operations demo failed: {e}")
        return False
    
    logger.info("Asset operations demo completed!")
    return True

def demo_key_rotation():
    """Demonstrate key rotation procedures."""
    logger.info("=== Key Rotation Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            # Initialize key manager
            key_manager = KeyManager(config, wallet.hsm)
            
            # Create a test key for rotation
            test_key_label = "rotation_test_key"
            
            try:
                logger.info("Creating test key for rotation...")
                pub_key, address = key_manager.create_stellar_key(
                    test_key_label,
                    description="Test key for rotation demo",
                    expires_days=1  # Short expiry for demo
                )
                logger.info(f"Test key created: {address}")
            except KeyManagerError as e:
                if "already exists" in str(e):
                    logger.info("Test key already exists")
                else:
                    raise
            
            # Simulate key usage
            logger.info("Simulating key usage...")
            for i in range(5):
                key_manager.use_key(test_key_label, f"demo_operation_{i}")
            
            # Check key status
            key_info = key_manager.get_key_info(test_key_label)
            logger.info(f"Key usage count: {key_info['usage_count']}")
            
            # Perform key rotation
            new_key_label = f"{test_key_label}_rotated"
            logger.info(f"Rotating key to: {new_key_label}")
            
            try:
                new_pub_key, new_address = key_manager.rotate_key(test_key_label, new_key_label)
                logger.info(f"Key rotated successfully to: {new_address}")
                
                # Verify old key is deactivated
                old_key_info = key_manager.get_key_info(test_key_label)
                new_key_info = key_manager.get_key_info(new_key_label)
                
                logger.info(f"Old key status: {old_key_info['status']}")
                logger.info(f"New key status: {new_key_info['status']}")
                
            except KeyManagerError as e:
                if "cancelled" in str(e):
                    logger.info("Key rotation was cancelled")
                else:
                    raise
            
    except Exception as e:
        logger.error(f"Key rotation demo failed: {e}")
        return False
    
    logger.info("Key rotation demo completed!")
    return True

def demo_compliance_audit():
    """Demonstrate compliance and audit features."""
    logger.info("=== Compliance and Audit Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            key_manager = KeyManager(config, wallet.hsm)
            
            # Generate comprehensive security report
            logger.info("Generating security report...")
            report = key_manager.get_security_report()
            
            logger.info("=== SECURITY REPORT ===")
            logger.info(f"Report generated at: {report['generated_at']}")
            logger.info(f"Total keys managed: {report['total_keys']}")
            
            # Key status summary
            logger.info("Key Status Summary:")
            for status, count in report['key_status_summary'].items():
                logger.info(f"  {status.upper()}: {count}")
            
            # Security issues
            if report['security_issues']:
                logger.warning("SECURITY ISSUES DETECTED:")
                for issue in report['security_issues']:
                    logger.warning(f"  {issue['severity'].upper()}: {issue['type']} - {issue['key_label']}")
            else:
                logger.info("No security issues detected ✓")
            
            # Expiring keys
            if report['expiring_keys']:
                logger.warning("KEYS EXPIRING SOON:")
                for key in report['expiring_keys']:
                    logger.warning(f"  {key['label']}: expires in {key['days_remaining']} days")
            else:
                logger.info("No keys expiring soon ✓")
            
            # High usage keys
            if report['high_usage_keys']:
                logger.info("HIGH USAGE KEYS:")
                for key in report['high_usage_keys']:
                    logger.info(f"  {key['label']}: {key['usage_count']} uses")
            
            # Inactive keys
            if report['inactive_keys']:
                logger.warning("INACTIVE KEYS:")
                for key in report['inactive_keys']:
                    logger.warning(f"  {key['label']}: last used {key['last_used'] or 'never'}")
            
            # Create audit trail backup
            backup_path = f"audit/security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            import json
            with open(backup_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Security report saved to: {backup_path}")
            
            # Backup key metadata
            metadata_backup_path = f"audit/key_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            if key_manager.backup_key_metadata(metadata_backup_path):
                logger.info(f"Key metadata backed up to: {metadata_backup_path}")
            
    except Exception as e:
        logger.error(f"Compliance audit demo failed: {e}")
        return False
    
    logger.info("Compliance audit demo completed!")
    return True

def demo_advanced_transactions():
    """Demonstrate advanced transaction types."""
    logger.info("=== Advanced Transaction Types Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            wallet.initialize_wallet()
            address = wallet.get_stellar_address()
            
            logger.info(f"Wallet address: {address}")
            
            # Demo various transaction types
            logger.info("Advanced transaction types would include:")
            
            # 1. Batch payments
            logger.info("1. Batch Payments:")
            logger.info("   - Multiple payments in single transaction")
            logger.info("   - Lower fees and faster processing")
            logger.info("   - Atomic execution (all or nothing)")
            
            # 2. Path payments
            logger.info("2. Path Payments:")
            logger.info("   - Currency conversion during payment")
            logger.info("   - Automatic pathfinding through DEX")
            logger.info("   - Cross-border payments with conversion")
            
            # 3. Account management operations
            logger.info("3. Account Management:")
            logger.info("   - Setting account thresholds")
            logger.info("   - Managing signers")
            logger.info("   - Account flags and options")
            
            # 4. Asset management
            logger.info("4. Asset Management:")
            logger.info("   - Creating and issuing custom assets")
            logger.info("   - Setting asset authorization flags")
            logger.info("   - Managing trustlines")
            
            # 5. DEX operations
            logger.info("5. Decentralized Exchange:")
            logger.info("   - Creating buy/sell offers")
            logger.info("   - Managing order book")
            logger.info("   - Automated market making")
            
            # Example: Create a complex transaction with multiple operations
            logger.info("Building sample complex transaction...")
            
            try:
                account_info = wallet.get_account_info()
                balance = wallet.get_balance("XLM")
                
                if balance > Decimal("5"):
                    logger.info("Sufficient balance for complex transaction demo")
                    
                    # In a real implementation, you could create a transaction with:
                    # - Payment operation
                    # - Manage data operation (setting account data)
                    # - Change trust operation (if working with assets)
                    
                    logger.info("Complex transaction would include:")
                    logger.info("  - Payment to recipient")
                    logger.info("  - Set account data field")
                    logger.info("  - Manage trustline to asset")
                    logger.info("  - All signed with HSM-protected key")
                    
                else:
                    logger.info("Insufficient balance for complex transaction demo")
                    
            except Exception as e:
                logger.warning(f"Could not check account for complex transaction: {e}")
            
    except Exception as e:
        logger.error(f"Advanced transactions demo failed: {e}")
        return False
    
    logger.info("Advanced transactions demo completed!")
    return True

def demo_disaster_recovery():
    """Demonstrate disaster recovery procedures."""
    logger.info("=== Disaster Recovery Demo ===")
    
    try:
        config = load_config()
        
        with StellarWallet(config) as wallet:
            key_manager = KeyManager(config, wallet.hsm)
            
            logger.info("Disaster Recovery Procedures:")
            
            # 1. Key backup verification
            logger.info("1. Key Backup Verification:")
            backup_path = "disaster_recovery/key_backup_test.json"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            if key_manager.backup_key_metadata(backup_path):
                logger.info("   ✓ Key metadata backup successful")
                
                # Verify backup integrity
                import json
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
                
                if backup_data.get('version') and backup_data.get('key_metadata'):
                    logger.info("   ✓ Backup integrity verified")
                else:
                    logger.error("   ✗ Backup integrity check failed")
            
            # 2. HSM connection test
            logger.info("2. HSM Connection Test:")
            try:
                if wallet.hsm.is_connected:
                    logger.info("   ✓ HSM connection active")
                    
                    # Test key operations
                    hsm_keys = wallet.hsm.list_keys()
                    logger.info(f"   ✓ Can access {len(hsm_keys)} keys in HSM")
                else:
                    logger.warning("   ✗ HSM not connected")
            except Exception as e:
                logger.error(f"   ✗ HSM test failed: {e}")
            
            # 3. Account recovery simulation
            logger.info("3. Account Recovery Procedures:")
            logger.info("   - Verify account exists on network")
            logger.info("   - Check account signers and thresholds")
            logger.info("   - Validate key access in HSM")
            logger.info("   - Test transaction signing capability")
            
            # 4. Security incident response
            logger.info("4. Security Incident Response:")
            logger.info("   - Immediate key deactivation procedures")
            logger.info("   - Emergency contact protocols")
            logger.info("   - Forensic data collection")
            logger.info("   - Recovery timeline planning")
            
            # 5. Business continuity
            logger.info("5. Business Continuity:")
            logger.info("   - Alternative signing mechanisms")
            logger.info("   - Backup HSM activation")
            logger.info("   - Service restoration procedures")
            logger.info("   - Stakeholder communication plan")
            
            # Generate disaster recovery report
            dr_report = {
                "timestamp": datetime.now().isoformat(),
                "hsm_status": "connected" if wallet.hsm.is_connected else "disconnected",
                "wallet_address": wallet.get_stellar_address(),
                "backup_status": "completed",
                "security_report": key_manager.get_security_report(),
                "recommendations": [
                    "Regular backup testing",
                    "HSM redundancy setup",
                    "Incident response drills",
                    "Recovery documentation updates"
                ]
            }
            
            dr_report_path = f"disaster_recovery/dr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(dr_report_path, 'w') as f:
                json.dump(dr_report, f, indent=2)
            
            logger.info(f"Disaster recovery report saved to: {dr_report_path}")
            
    except Exception as e:
        logger.error(f"Disaster recovery demo failed: {e}")
        return False
    
    logger.info("Disaster recovery demo completed!")
    return True

def main():
    """Main function to run all advanced demos."""
    setup_logging()
    
    logger.info("Starting Advanced Stellar Wallet with Dinamo HSM Features...")
    
    # Check HSM_USER_PIN environment variable
    if not os.getenv('HSM_USER_PIN'):
        logger.error("HSM_USER_PIN environment variable not set!")
        logger.info("Please set your HSM user PIN: export HSM_USER_PIN=your_pin")
        return 1
    
    demos = [
        ("Multi-Signature Setup", demo_multisig_setup),
        ("Asset Operations", demo_asset_operations),
        ("Key Rotation", demo_key_rotation),
        ("Compliance & Audit", demo_compliance_audit),
        ("Advanced Transactions", demo_advanced_transactions),
        ("Disaster Recovery", demo_disaster_recovery),
    ]
    
    success_count = 0
    
    for demo_name, demo_func in demos:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {demo_name}")
        logger.info(f"{'='*50}")
        
        try:
            if demo_func():
                success_count += 1
                logger.info(f"✓ {demo_name} completed successfully")
            else:
                logger.error(f"✗ {demo_name} failed")
        except Exception as e:
            logger.error(f"✗ {demo_name} failed with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Advanced Features Demo Summary")
    logger.info(f"{'='*50}")
    logger.info(f"Completed: {success_count}/{len(demos)} demos")
    
    if success_count == len(demos):
        logger.info("All advanced features demos completed successfully! 🎉")
        return 0
    else:
        logger.warning(f"{len(demos) - success_count} demos had issues")
        return 1

if __name__ == "__main__":
    exit(main())