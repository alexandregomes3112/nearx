# Stellar Wallet with Dinamo HSM Integration

A secure, enterprise-grade Stellar blockchain wallet implementation that uses Dinamo HSM (Hardware Security Module) for cryptographic key management and transaction signing.

## 🔐 Features

- **HSM-Secured Key Storage**: Private keys never leave the HSM
- **PKCS#11 Compliance**: Standard interface for HSM integration
- **Advanced Key Management**: Key lifecycle, rotation, and audit trails
- **Stellar Network Support**: Full integration with Stellar blockchain
- **Multi-signature Ready**: Support for complex signing scenarios
- **Comprehensive Auditing**: Security reporting and compliance features
- **Disaster Recovery**: Backup and recovery procedures

## 📋 Prerequisites

### Hardware Requirements
- Dinamo HSM device (or compatible PKCS#11 HSM)
- Linux system (tested on Ubuntu 20.04+, CentOS 7+)
- Minimum 4GB RAM, 10GB disk space

### Software Requirements
- Python 3.9 or higher
- Dinamo HSM PKCS#11 library installed
- Stellar SDK dependencies

### Network Access
- Connection to Stellar Horizon server (testnet or mainnet)
- HSM device connectivity (USB/Network)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd stellar-wallet-dinamo-hsm

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
```

### 2. Configuration

Edit `config.yaml` with your HSM and Stellar settings:

```yaml
stellar:
  network: "TESTNET"  # or "MAINNET"
  horizon_url: "https://horizon-testnet.stellar.org"

hsm:
  pkcs11_lib_path: "/usr/lib/libdinamo.so"
  slot_id: 0
  token_label: "dinamo_token"
  key_label: "stellar_wallet_key"
```

Set your HSM PIN in environment variables:

```bash
export HSM_USER_PIN=your_hsm_pin_here
```

### 3. Basic Usage

```python
from src.stellar_wallet import StellarWallet
import yaml

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize and use wallet
with StellarWallet(config) as wallet:
    # Initialize wallet (creates/loads keys from HSM)
    address = wallet.initialize_wallet()
    print(f"Wallet address: {address}")
    
    # Check balance
    balance = wallet.get_balance("XLM")
    print(f"Balance: {balance} XLM")
    
    # Send payment
    tx_hash = wallet.send_payment(
        destination="GDLP3SP4WP72L4BAJWZUDZ6SAYE4NAWILT5WQDS7RWC4XCUNUQDRB2A4",
        amount="10.5",
        memo="Payment from HSM wallet"
    )
    print(f"Transaction: {tx_hash}")
```

## 📚 Documentation

### Core Components

#### 1. DinamoHSM (`src/dinamo_hsm.py`)
- PKCS#11 interface to Dinamo HSM
- Key generation and management
- Secure signing operations
- HSM device lifecycle management

#### 2. StellarWallet (`src/stellar_wallet.py`)
- Main wallet interface
- Transaction building and submission
- Account management
- Balance queries and payments

#### 3. KeyManager (`src/key_manager.py`)
- Advanced key lifecycle management
- Usage tracking and auditing
- Key rotation procedures
- Security policy enforcement

### API Reference

#### StellarWallet Class

```python
class StellarWallet:
    def __init__(self, config: Dict[str, Any])
    def initialize_wallet(self, generate_new: bool = False) -> str
    def get_account_info(self) -> Dict[str, Any]
    def get_balance(self, asset_code: str = "XLM") -> Decimal
    def send_payment(self, destination: str, amount: str, ...) -> str
    def create_account(self, new_account_address: str, ...) -> str
    def get_transaction_history(self, limit: int = 10) -> List[Dict]
```

#### KeyManager Class

```python
class KeyManager:
    def __init__(self, config: Dict[str, Any], hsm: DinamoHSM)
    def create_stellar_key(self, key_label: str, ...) -> Tuple[str, str]
    def get_key_info(self, key_label: str) -> Dict[str, Any]
    def use_key(self, key_label: str, operation: str) -> bool
    def rotate_key(self, old_label: str, new_label: str) -> Tuple[str, str]
    def get_security_report(self) -> Dict[str, Any]
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `HSM_USER_PIN` | HSM user authentication PIN | Yes |
| `STELLAR_NETWORK` | Network override (TESTNET/MAINNET) | No |
| `HORIZON_URL` | Horizon server URL override | No |
| `PKCS11_LIB_PATH` | HSM library path override | No |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | No |

### Configuration File Structure

```yaml
stellar:
  network: "TESTNET"              # Stellar network
  horizon_url: "https://..."      # Horizon server URL
  base_fee: 100                   # Transaction base fee (stroops)
  timeout: 30                     # Transaction timeout (seconds)

hsm:
  pkcs11_lib_path: "/usr/lib/..."  # PKCS#11 library path
  slot_id: 0                      # HSM slot ID
  token_label: "dinamo_token"     # Token label
  key_label: "stellar_key"        # Default key label
  key_type: "EC"                  # Key type (EC/RSA)
  ec_curve: "secp256k1"          # EC curve for Stellar

security:
  require_user_confirmation: true  # Require confirmation for operations
  audit_logging: true             # Enable audit logging
  key_backup_required: false      # Require key backups

logging:
  level: "INFO"                   # Log level
  file: "stellar_wallet.log"      # Log file path
```

## 💡 Examples

### Running Examples

1. **Basic Usage Example**:
```bash
# Set your HSM PIN
export HSM_USER_PIN=your_pin

# Run basic demo
python examples/basic_usage.py

# Run in interactive mode
python examples/basic_usage.py --interactive
```

2. **Advanced Features Example**:
```bash
python examples/advanced_features.py
```

### Example Scripts

- `examples/basic_usage.py` - Basic wallet operations
- `examples/advanced_features.py` - Advanced features demo

### Funding Your Testnet Account

For testnet usage, fund your account using Stellar's Friendbot:

```bash
# Get your wallet address first, then visit:
https://friendbot.stellar.org?addr=YOUR_WALLET_ADDRESS
```

## 🔒 Security

### Key Security
- Private keys never leave the HSM
- FIPS 140-2 Level 3 security (HSM dependent)
- Secure key generation using hardware entropy
- Non-extractable key storage

### Operational Security
- User PIN authentication required
- Audit logging for all operations
- Key usage tracking and monitoring
- Automatic key expiration support

### Compliance Features
- Comprehensive audit trails
- Security reporting and monitoring
- Key lifecycle management
- Disaster recovery procedures

## 🛡️ Best Practices

### Key Management
1. **Regular Key Rotation**: Implement periodic key rotation
2. **Access Control**: Limit HSM access to authorized personnel
3. **Backup Procedures**: Maintain secure metadata backups
4. **Monitoring**: Monitor key usage and security reports

### Operational Security
1. **Environment Variables**: Use environment variables for sensitive data
2. **Network Security**: Secure communication channels
3. **Audit Logging**: Enable and monitor audit logs
4. **Testing**: Regular testing of backup and recovery procedures

### Development
1. **Use Testnet**: Test thoroughly on Stellar testnet first
2. **Error Handling**: Implement comprehensive error handling
3. **Logging**: Use appropriate logging levels
4. **Documentation**: Maintain up-to-date documentation

## 🐛 Troubleshooting

### Common Issues

#### HSM Connection Problems
```bash
# Check HSM library path
ls -la /usr/lib/libdinamo.so

# Verify HSM device connection
# (HSM-specific commands)

# Check slot availability
# Use HSM vendor tools to verify slots
```

#### Key Generation Failures
```bash
# Verify HSM PIN
echo $HSM_USER_PIN

# Check HSM capacity
# Ensure sufficient space for new keys

# Verify permissions
# Check user permissions for HSM access
```

#### Network Connectivity Issues
```bash
# Test Horizon connectivity
curl https://horizon-testnet.stellar.org/

# Check account funding (testnet)
# Use Friendbot for testnet funding

# Verify network configuration
# Check config.yaml network settings
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python examples/basic_usage.py
```

### Support

For additional support:
1. Check the logs in `stellar_wallet.log`
2. Review HSM vendor documentation
3. Consult Stellar SDK documentation
4. Check network status on Stellar Dashboard

## 📊 Monitoring and Compliance

### Security Reports

Generate security reports for compliance:

```python
from src.key_manager import KeyManager

key_manager = KeyManager(config, hsm)
report = key_manager.get_security_report()

# Report includes:
# - Key status summary
# - Expiring keys
# - High usage keys
# - Security issues
# - Compliance metrics
```

### Audit Logging

All security-relevant operations are logged:
- Key creation and rotation
- Transaction signing
- HSM access events
- Security policy violations

### Backup Procedures

Regular backups of key metadata:

```python
# Backup key metadata
backup_path = f"backups/keys_{datetime.now().strftime('%Y%m%d')}.json"
key_manager.backup_key_metadata(backup_path)
```

## 🚧 Development

### Setting up Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest black flake8

# Run tests
pytest tests/

# Format code
black src/ examples/

# Lint code
flake8 src/ examples/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Stellar Development Foundation](https://stellar.org) for the Stellar network
- [Dinamo Networks](https://dinamonetworks.com) for HSM technology
- PKCS#11 standard contributors
- Python cryptographic libraries community

## 📞 Support

For technical support and questions:
- Documentation: Review this README and code comments
- Issues: Submit GitHub issues for bugs and feature requests
- Community: Join Stellar developer community forums

---

**⚠️ Security Notice**: This software handles cryptographic keys and financial transactions. Always test thoroughly in a safe environment before production use. Ensure your HSM device is properly configured and secured according to your organization's security policies.
