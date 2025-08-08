"""
Stellar Wallet Implementation with Dinamo HSM Integration

This module provides a secure Stellar wallet implementation that uses
Dinamo HSM for private key storage and transaction signing.
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

from stellar_sdk import (
    Server, Keypair, TransactionBuilder, Network, Asset,
    Account, Transaction, TransactionEnvelope
)
from stellar_sdk.exceptions import (
    StellarSdkError, BadResponseError, NotFoundError
)

from .dinamo_hsm import DinamoHSM, DinamoHSMError

logger = logging.getLogger(__name__)


class StellarWalletError(Exception):
    """Custom exception for Stellar wallet operations"""
    pass


class StellarWallet:
    """
    Secure Stellar wallet implementation using Dinamo HSM.
    
    This wallet provides:
    - HSM-secured private key storage
    - Transaction creation and signing
    - Account management
    - Balance queries
    - Payment operations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Stellar wallet.
        
        Args:
            config: Configuration dictionary containing Stellar and HSM settings
        """
        self.config = config
        self.stellar_config = config.get('stellar', {})
        self.hsm_config = config.get('hsm', {})
        
        # Initialize Stellar SDK components
        self.network = self.stellar_config.get('network', 'TESTNET')
        self.horizon_url = self.stellar_config.get('horizon_url', 'https://horizon-testnet.stellar.org')
        self.base_fee = self.stellar_config.get('base_fee', 100)
        self.timeout = self.stellar_config.get('timeout', 30)
        
        # Set network passphrase
        if self.network == 'TESTNET':
            self.network_passphrase = Network.TESTNET_NETWORK_PASSPHRASE
        elif self.network == 'MAINNET':
            self.network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE
        else:
            raise StellarWalletError(f"Invalid network: {self.network}")
        
        # Initialize Horizon server
        self.server = Server(horizon_url=self.horizon_url)
        
        # Initialize HSM
        self.hsm = DinamoHSM(self.hsm_config)
        
        # Wallet state
        self.public_key = None
        self.stellar_address = None
        self.account = None
        
        logger.info(f"Initialized Stellar wallet for {self.network} network")
    
    def initialize_wallet(self, generate_new: bool = False) -> str:
        """
        Initialize the wallet by connecting to HSM and loading/generating keys.
        
        Args:
            generate_new: Whether to generate a new key pair
            
        Returns:
            str: Stellar address of the wallet
            
        Raises:
            StellarWalletError: If initialization fails
        """
        try:
            logger.info("Initializing Stellar wallet with HSM...")
            
            # Connect to HSM
            self.hsm.connect()
            
            if generate_new:
                # Generate new key pair in HSM
                logger.info("Generating new key pair in HSM")
                self.public_key, self.stellar_address = self.hsm.generate_keypair(overwrite=True)
            else:
                # Try to load existing key pair
                try:
                    self.public_key, self.stellar_address = self.hsm.get_public_key()
                    logger.info(f"Loaded existing key pair. Address: {self.stellar_address}")
                except DinamoHSMError:
                    # No existing key found, generate new one
                    logger.info("No existing key found, generating new key pair")
                    self.public_key, self.stellar_address = self.hsm.generate_keypair()
            
            logger.info(f"Wallet initialized successfully. Address: {self.stellar_address}")
            return self.stellar_address
            
        except DinamoHSMError as e:
            logger.error(f"HSM error during wallet initialization: {e}")
            raise StellarWalletError(f"Failed to initialize wallet: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during wallet initialization: {e}")
            raise StellarWalletError(f"Unexpected error initializing wallet: {e}")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from Stellar network.
        
        Returns:
            Dict[str, Any]: Account information including balances, sequence, etc.
            
        Raises:
            StellarWalletError: If account retrieval fails
        """
        if not self.stellar_address:
            raise StellarWalletError("Wallet not initialized")
        
        try:
            logger.debug(f"Fetching account info for {self.stellar_address}")
            
            # Load account from Stellar network
            account_response = self.server.accounts().account_id(self.stellar_address).call()
            
            # Parse account information
            account_info = {
                'account_id': account_response['account_id'],
                'sequence': account_response['sequence'],
                'balances': account_response['balances'],
                'signers': account_response['signers'],
                'flags': account_response['flags'],
                'thresholds': account_response['thresholds'],
                'data': account_response.get('data', {}),
                'num_sponsoring': account_response.get('num_sponsoring', 0),
                'num_sponsored': account_response.get('num_sponsored', 0)
            }
            
            # Cache account for transaction building
            self.account = Account(
                account_id=account_response['account_id'],
                sequence=int(account_response['sequence'])
            )
            
            return account_info
            
        except NotFoundError:
            logger.warning(f"Account {self.stellar_address} not found on network")
            raise StellarWalletError(f"Account {self.stellar_address} not found. Account may need to be funded.")
        except BadResponseError as e:
            logger.error(f"Bad response from Horizon server: {e}")
            raise StellarWalletError(f"Failed to fetch account info: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching account info: {e}")
            raise StellarWalletError(f"Unexpected error fetching account info: {e}")
    
    def get_balance(self, asset_code: str = "XLM") -> Decimal:
        """
        Get balance for a specific asset.
        
        Args:
            asset_code: Asset code (default: "XLM" for native Lumens)
            
        Returns:
            Decimal: Balance amount
            
        Raises:
            StellarWalletError: If balance retrieval fails
        """
        try:
            account_info = self.get_account_info()
            balances = account_info['balances']
            
            for balance in balances:
                if asset_code == "XLM" and balance['asset_type'] == 'native':
                    return Decimal(balance['balance'])
                elif balance.get('asset_code') == asset_code:
                    return Decimal(balance['balance'])
            
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Error getting balance for {asset_code}: {e}")
            raise StellarWalletError(f"Failed to get balance: {e}")
    
    def send_payment(self, 
                    destination: str, 
                    amount: str, 
                    asset_code: str = "XLM",
                    asset_issuer: Optional[str] = None,
                    memo: Optional[str] = None) -> str:
        """
        Send a payment to another Stellar account.
        
        Args:
            destination: Destination Stellar address
            amount: Amount to send
            asset_code: Asset code (default: "XLM")
            asset_issuer: Asset issuer (required for non-native assets)
            memo: Optional memo text
            
        Returns:
            str: Transaction hash
            
        Raises:
            StellarWalletError: If payment fails
        """
        if not self.stellar_address:
            raise StellarWalletError("Wallet not initialized")
        
        try:
            logger.info(f"Sending {amount} {asset_code} to {destination}")
            
            # Get account info to update sequence
            self.get_account_info()
            
            if not self.account:
                raise StellarWalletError("Account not loaded")
            
            # Create asset object
            if asset_code == "XLM":
                asset = Asset.native()
            else:
                if not asset_issuer:
                    raise StellarWalletError("Asset issuer required for non-native assets")
                asset = Asset(asset_code, asset_issuer)
            
            # Build transaction
            transaction_builder = TransactionBuilder(
                source_account=self.account,
                network_passphrase=self.network_passphrase,
                base_fee=self.base_fee
            )
            
            # Add payment operation
            transaction_builder.append_payment_op(
                destination=destination,
                asset=asset,
                amount=amount
            )
            
            # Add memo if provided
            if memo:
                transaction_builder.add_text_memo(memo)
            
            # Set timeout
            transaction_builder.set_timeout(self.timeout)
            
            # Build transaction
            transaction = transaction_builder.build()
            
            # Sign transaction with HSM
            signed_transaction = self._sign_transaction(transaction)
            
            # Submit transaction
            response = self.server.submit_transaction(signed_transaction)
            
            transaction_hash = response['hash']
            logger.info(f"Payment sent successfully. Transaction hash: {transaction_hash}")
            
            return transaction_hash
            
        except StellarSdkError as e:
            logger.error(f"Stellar SDK error during payment: {e}")
            raise StellarWalletError(f"Payment failed: {e}")
        except DinamoHSMError as e:
            logger.error(f"HSM error during payment: {e}")
            raise StellarWalletError(f"Payment failed (HSM error): {e}")
        except Exception as e:
            logger.error(f"Unexpected error during payment: {e}")
            raise StellarWalletError(f"Unexpected error during payment: {e}")
    
    def create_account(self, 
                      new_account_address: str, 
                      starting_balance: str = "1") -> str:
        """
        Create a new Stellar account.
        
        Args:
            new_account_address: Address of the new account to create
            starting_balance: Starting balance for the new account
            
        Returns:
            str: Transaction hash
            
        Raises:
            StellarWalletError: If account creation fails
        """
        if not self.stellar_address:
            raise StellarWalletError("Wallet not initialized")
        
        try:
            logger.info(f"Creating account {new_account_address} with balance {starting_balance} XLM")
            
            # Get account info
            self.get_account_info()
            
            if not self.account:
                raise StellarWalletError("Account not loaded")
            
            # Build transaction
            transaction_builder = TransactionBuilder(
                source_account=self.account,
                network_passphrase=self.network_passphrase,
                base_fee=self.base_fee
            )
            
            # Add create account operation
            transaction_builder.append_create_account_op(
                destination=new_account_address,
                starting_balance=starting_balance
            )
            
            # Set timeout
            transaction_builder.set_timeout(self.timeout)
            
            # Build transaction
            transaction = transaction_builder.build()
            
            # Sign transaction with HSM
            signed_transaction = self._sign_transaction(transaction)
            
            # Submit transaction
            response = self.server.submit_transaction(signed_transaction)
            
            transaction_hash = response['hash']
            logger.info(f"Account created successfully. Transaction hash: {transaction_hash}")
            
            return transaction_hash
            
        except StellarSdkError as e:
            logger.error(f"Stellar SDK error during account creation: {e}")
            raise StellarWalletError(f"Account creation failed: {e}")
        except DinamoHSMError as e:
            logger.error(f"HSM error during account creation: {e}")
            raise StellarWalletError(f"Account creation failed (HSM error): {e}")
        except Exception as e:
            logger.error(f"Unexpected error during account creation: {e}")
            raise StellarWalletError(f"Unexpected error during account creation: {e}")
    
    def get_transaction_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get transaction history for the wallet.
        
        Args:
            limit: Maximum number of transactions to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of transaction records
            
        Raises:
            StellarWalletError: If retrieval fails
        """
        if not self.stellar_address:
            raise StellarWalletError("Wallet not initialized")
        
        try:
            logger.debug(f"Fetching transaction history for {self.stellar_address}")
            
            # Get transactions
            transactions_response = (
                self.server.transactions()
                .for_account(self.stellar_address)
                .order(desc=True)
                .limit(limit)
                .call()
            )
            
            transactions = []
            for tx_record in transactions_response['_embedded']['records']:
                transaction = {
                    'hash': tx_record['hash'],
                    'ledger': tx_record['ledger'],
                    'created_at': tx_record['created_at'],
                    'source_account': tx_record['source_account'],
                    'fee': tx_record['fee_charged'],
                    'operation_count': tx_record['operation_count'],
                    'memo': tx_record.get('memo'),
                    'memo_type': tx_record.get('memo_type'),
                    'successful': tx_record['successful']
                }
                transactions.append(transaction)
            
            return transactions
            
        except BadResponseError as e:
            logger.error(f"Bad response from Horizon server: {e}")
            raise StellarWalletError(f"Failed to fetch transaction history: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching transaction history: {e}")
            raise StellarWalletError(f"Unexpected error fetching transaction history: {e}")
    
    def _sign_transaction(self, transaction: Transaction) -> TransactionEnvelope:
        """
        Sign a transaction using the HSM-stored private key.
        
        Args:
            transaction: Transaction to sign
            
        Returns:
            TransactionEnvelope: Signed transaction
            
        Raises:
            StellarWalletError: If signing fails
        """
        try:
            logger.debug("Signing transaction with HSM")
            
            # Get transaction hash
            tx_hash = transaction.hash()
            
            # Sign with HSM
            signature = self.hsm.sign_data(tx_hash)
            
            # Create transaction envelope
            envelope = TransactionEnvelope(transaction, self.network_passphrase)
            
            # Add signature to envelope
            # Note: This is simplified - in practice, you need to properly
            # format the signature and add it to the envelope
            envelope.signatures.append(signature)
            
            logger.debug("Transaction signed successfully")
            return envelope
            
        except DinamoHSMError as e:
            logger.error(f"HSM error during transaction signing: {e}")
            raise StellarWalletError(f"Failed to sign transaction: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during transaction signing: {e}")
            raise StellarWalletError(f"Unexpected error signing transaction: {e}")
    
    def get_stellar_address(self) -> Optional[str]:
        """Get the Stellar address of this wallet."""
        return self.stellar_address
    
    def get_public_key_hex(self) -> Optional[str]:
        """Get the public key in hex format."""
        return self.public_key
    
    def is_initialized(self) -> bool:
        """Check if the wallet is initialized."""
        return self.stellar_address is not None
    
    def list_hsm_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        List all keys in the HSM.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of key information
        """
        try:
            if not self.hsm.is_connected:
                self.hsm.connect()
            
            return self.hsm.list_keys()
            
        except DinamoHSMError as e:
            logger.error(f"HSM error listing keys: {e}")
            raise StellarWalletError(f"Failed to list HSM keys: {e}")
    
    def close(self):
        """Close the wallet and disconnect from HSM."""
        try:
            if self.hsm:
                self.hsm.disconnect()
            logger.info("Wallet closed successfully")
        except Exception as e:
            logger.warning(f"Error closing wallet: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()