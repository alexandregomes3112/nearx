#!/usr/bin/env python3
"""
Basic Usage Example for Stellar Wallet with Dinamo HSM

This example demonstrates how to:
1. Initialize the wallet with HSM
2. Create or load a key pair
3. Check account balance
4. Send payments
5. View transaction history
6. Manage keys securely
"""

import os
import sys
import yaml
import logging
from decimal import Decimal
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.stellar_wallet import StellarWallet, StellarWalletError
from src.key_manager import KeyManager, KeyManagerError
from loguru import logger

def setup_logging():
    """Set up logging configuration."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
        level="INFO"
    )
    logger.add(
        "stellar_wallet.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
        level="DEBUG",
        rotation="10 MB"
    )

def load_config():
    """Load configuration from file and environment variables."""
    # Load environment variables
    load_dotenv()
    
    # Load configuration file
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables
    hsm_config = config['hsm']
    if os.getenv('HSM_USER_PIN'):
        hsm_config['user_pin'] = os.getenv('HSM_USER_PIN')
    if os.getenv('PKCS11_LIB_PATH'):
        hsm_config['pkcs11_lib_path'] = os.getenv('PKCS11_LIB_PATH')
    
    stellar_config = config['stellar']
    if os.getenv('STELLAR_NETWORK'):
        stellar_config['network'] = os.getenv('STELLAR_NETWORK')
    if os.getenv('HORIZON_URL'):
        stellar_config['horizon_url'] = os.getenv('HORIZON_URL')
    
    return config

def demo_basic_wallet_operations():
    """Demonstrate basic wallet operations."""
    logger.info("=== Stellar Wallet with Dinamo HSM Demo ===")
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize wallet
        with StellarWallet(config) as wallet:
            logger.info("Stellar wallet initialized")
            
            # Initialize wallet (this will create/load keys from HSM)
            stellar_address = wallet.initialize_wallet(generate_new=False)
            logger.info(f"Wallet address: {stellar_address}")
            
            # Get account information
            try:
                account_info = wallet.get_account_info()
                logger.info("Account information:")
                logger.info(f"  Account ID: {account_info['account_id']}")
                logger.info(f"  Sequence: {account_info['sequence']}")
                logger.info(f"  Balances:")
                for balance in account_info['balances']:
                    if balance['asset_type'] == 'native':
                        logger.info(f"    XLM: {balance['balance']}")
                    else:
                        asset_code = balance.get('asset_code', 'Unknown')
                        logger.info(f"    {asset_code}: {balance['balance']}")
                
            except StellarWalletError as e:
                if "not found" in str(e):
                    logger.warning("Account not found on network. Account needs to be funded.")
                    logger.info(f"To fund your testnet account, visit: https://friendbot.stellar.org?addr={stellar_address}")
                else:
                    logger.error(f"Error getting account info: {e}")
                return
            
            # Get XLM balance
            xlm_balance = wallet.get_balance("XLM")
            logger.info(f"XLM Balance: {xlm_balance}")
            
            # Get transaction history
            logger.info("Recent transactions:")
            try:
                transactions = wallet.get_transaction_history(limit=5)
                for i, tx in enumerate(transactions, 1):
                    logger.info(f"  {i}. Hash: {tx['hash'][:8]}... | "
                              f"Fee: {tx['fee']} stroops | "
                              f"Successful: {tx['successful']} | "
                              f"Date: {tx['created_at']}")
            except Exception as e:
                logger.warning(f"Could not fetch transaction history: {e}")
            
            # Demo payment (if balance is sufficient)
            if xlm_balance > Decimal("2"):
                demo_destination = "GDLP3SP4WP72L4BAJWZUDZ6SAYE4NAWILT5WQDS7RWC4XCUNUQDRB2A4"  # Example address
                payment_amount = "1.5"
                
                logger.info(f"Sending {payment_amount} XLM to {demo_destination}")
                try:
                    # Note: This would actually send a transaction in a real scenario
                    # For demo purposes, we'll skip the actual sending
                    logger.info("Payment demo skipped (would send real transaction)")
                    
                    # Uncomment the following lines to send a real payment:
                    # tx_hash = wallet.send_payment(
                    #     destination=demo_destination,
                    #     amount=payment_amount,
                    #     memo="Demo payment from HSM wallet"
                    # )
                    # logger.info(f"Payment sent! Transaction hash: {tx_hash}")
                    
                except StellarWalletError as e:
                    logger.error(f"Payment failed: {e}")
            else:
                logger.info("Insufficient balance for payment demo")
            
            # List HSM keys
            logger.info("Keys in HSM:")
            try:
                hsm_keys = wallet.list_hsm_keys()
                for label, key_info in hsm_keys.items():
                    logger.info(f"  {label}: {key_info}")
            except Exception as e:
                logger.warning(f"Could not list HSM keys: {e}")
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return False
    
    logger.info("Demo completed successfully!")
    return True

def demo_key_management():
    """Demonstrate advanced key management features."""
    logger.info("=== Key Management Demo ===")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize wallet and key manager
        with StellarWallet(config) as wallet:
            key_manager = KeyManager(config, wallet.hsm)
            
            # Create a new key
            logger.info("Creating a new test key...")
            try:
                pub_key, address = key_manager.create_stellar_key(
                    "demo_key_1",
                    description="Demo key for testing",
                    expires_days=365
                )
                logger.info(f"Created key: {address}")
            except KeyManagerError as e:
                if "already exists" in str(e):
                    logger.info("Demo key already exists, using existing key")
                else:
                    raise
            
            # List all keys
            logger.info("All managed keys:")
            keys = key_manager.list_keys()
            for key_info in keys:
                logger.info(f"  {key_info['label']}: {key_info['status']} "
                          f"(created: {key_info['created_at']}, "
                          f"used: {key_info['usage_count']} times)")
            
            # Generate security report
            logger.info("Security report:")
            report = key_manager.get_security_report()
            logger.info(f"  Total keys: {report['total_keys']}")
            logger.info(f"  Status summary: {report['key_status_summary']}")
            
            if report['expiring_keys']:
                logger.warning(f"  Expiring keys: {len(report['expiring_keys'])}")
            
            if report['security_issues']:
                logger.warning(f"  Security issues: {len(report['security_issues'])}")
            
            # Backup metadata
            backup_path = "backups/key_metadata_backup.json"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            if key_manager.backup_key_metadata(backup_path):
                logger.info(f"Key metadata backed up to {backup_path}")
            
    except Exception as e:
        logger.error(f"Key management demo failed: {e}")
        return False
    
    logger.info("Key management demo completed!")
    return True

def interactive_mode():
    """Interactive mode for manual testing."""
    logger.info("=== Interactive Mode ===")
    logger.info("Available commands:")
    logger.info("  1. Check balance")
    logger.info("  2. Send payment")
    logger.info("  3. View transaction history")
    logger.info("  4. Create new key")
    logger.info("  5. List keys")
    logger.info("  6. Security report")
    logger.info("  0. Exit")
    
    config = load_config()
    
    with StellarWallet(config) as wallet:
        wallet.initialize_wallet(generate_new=False)
        key_manager = KeyManager(config, wallet.hsm)
        
        while True:
            try:
                choice = input("\nEnter command number: ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    balance = wallet.get_balance("XLM")
                    logger.info(f"Current XLM balance: {balance}")
                    
                elif choice == "2":
                    dest = input("Destination address: ").strip()
                    amount = input("Amount (XLM): ").strip()
                    memo = input("Memo (optional): ").strip() or None
                    
                    try:
                        tx_hash = wallet.send_payment(dest, amount, memo=memo)
                        logger.info(f"Payment sent! Transaction: {tx_hash}")
                    except Exception as e:
                        logger.error(f"Payment failed: {e}")
                        
                elif choice == "3":
                    limit = int(input("Number of transactions (default 10): ").strip() or "10")
                    transactions = wallet.get_transaction_history(limit)
                    
                    for i, tx in enumerate(transactions, 1):
                        logger.info(f"{i}. {tx['hash'][:8]}... | "
                                  f"Fee: {tx['fee']} | "
                                  f"Success: {tx['successful']} | "
                                  f"{tx['created_at']}")
                        
                elif choice == "4":
                    label = input("Key label: ").strip()
                    desc = input("Description (optional): ").strip() or None
                    days = input("Expiry days (optional): ").strip()
                    days = int(days) if days else None
                    
                    try:
                        pub_key, address = key_manager.create_stellar_key(label, desc, days)
                        logger.info(f"Key created! Address: {address}")
                    except Exception as e:
                        logger.error(f"Key creation failed: {e}")
                        
                elif choice == "5":
                    keys = key_manager.list_keys()
                    logger.info(f"Found {len(keys)} keys:")
                    for key_info in keys:
                        logger.info(f"  {key_info['label']}: {key_info['status']}")
                        
                elif choice == "6":
                    report = key_manager.get_security_report()
                    logger.info("Security Report:")
                    logger.info(f"  Total keys: {report['total_keys']}")
                    logger.info(f"  Status: {report['key_status_summary']}")
                    if report['security_issues']:
                        logger.warning(f"  Issues: {len(report['security_issues'])}")
                        
                else:
                    logger.warning("Invalid command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Command failed: {e}")
    
    logger.info("Interactive mode ended")

def main():
    """Main function."""
    setup_logging()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        # Run demos
        logger.info("Starting Stellar Wallet with Dinamo HSM demos...")
        
        # Check HSM_USER_PIN environment variable
        if not os.getenv('HSM_USER_PIN'):
            logger.error("HSM_USER_PIN environment variable not set!")
            logger.info("Please set your HSM user PIN: export HSM_USER_PIN=your_pin")
            return 1
        
        success = True
        
        # Run basic wallet demo
        if not demo_basic_wallet_operations():
            success = False
        
        # Run key management demo
        if not demo_key_management():
            success = False
        
        if success:
            logger.info("All demos completed successfully!")
            logger.info("To run in interactive mode: python basic_usage.py --interactive")
            return 0
        else:
            logger.error("Some demos failed!")
            return 1

if __name__ == "__main__":
    exit(main())