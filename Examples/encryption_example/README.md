# 🔐 Encryption Example

This example project provides a comprehensive demonstration of the `system_encryption` module within the **Massir framework**. It showcases how to integrate and utilize stateless cryptographic operations across a modular, plugin-based application architecture.

## 🎯 Features Demonstrated

### 1. Symmetric Encryption (AES-256-GCM)
- Generation of secure AES-256 keys.
- Data encryption and decryption.
- Usage of Associated Authenticated Data (AAD) for enhanced integrity.
- Proper management of nonces and authentication tags.

### 2. Asymmetric Encryption (RSA-4096)
- Generation of RSA key pairs (public/private).
- Data encryption using the public key and decryption using the private key.
- Creation and verification of digital signatures.

### 3. Message Authentication (HMAC)
- Generation of HMAC signatures for data integrity and authenticity.
- Verification of message origins.
- Support for multiple hash algorithms (SHA-256, SHA-384, SHA-512, SHA3).

### 4. Key Management & Serialization
- Exporting and importing public keys (PEM/DER formats).
- Password-protected exporting and importing of private keys.
- Generation of cryptographically secure random bytes.

---

## 📦 Project Modules

This example leverages Massir's modular architecture by splitting the logic into two distinct application modules:

### `encryption_tester`
An automated testing module that executes a full suite of cryptographic operations on startup. It catches exceptions, verifies outputs, and displays detailed, color-coded results in the console to ensure the `encryption_api` is functioning correctly.

### `encryption_demo`
A demonstration module that acts as a service layer. It consumes the core `encryption_api` and exposes a higher-level `encryption_service` for other application modules to easily encrypt strings, dictionaries, or sign messages without dealing with low-level byte conversions.

---

## 🚀 How to Run

Ensure you have the required dependencies installed (primarily the `cryptography` library) and run the main entry point:

```bash
cd Examples/encryption_example
pip install cryptography  # If not already installed via massir requirements
python main.py
```

## 📊 Expected Output

```text
==========================================================
    Encryption Example
    1.0.0
    Example demonstrating system_encryption module usage
==========================================================

[INFO]    EncryptionModule loaded - AES-256-GCM, RSA-4096, HMAC-SHA256 ready
[INFO]    EncryptionTester module loaded
[INFO]    EncryptionDemo module loaded - encryption_service available

==================================================
🔐 Starting Encryption Tests
==================================================

[INFO]    ✅ AES-256-GCM Test: PASSED
[INFO]    ✅ RSA-4096 Encryption Test: PASSED
[INFO]    ✅ RSA-4096 Signing Test: PASSED
[INFO]    ✅ HMAC-SHA256 Test: PASSED
[INFO]    ✅ Key Export/Import Test: PASSED
[INFO]    ✅ Integration Test: PASSED

============================================================
📊 Test Summary: 5/5 categories passed
  aes: ✅ PASSED (5/5 subtests)
  rsa: ✅ PASSED (4/4 subtests)
  hmac: ✅ PASSED (3/3 subtests)
  key_management: ✅ PASSED (2/2 subtests)
  integration: ✅ PASSED (2/2 subtests)

🎉 All encryption tests completed successfully!
============================================================
```

---

## ⚙️ Configuration

Because Massir supports dynamic configuration, module-specific settings are managed via `app_settings.json`. The `system_encryption` module reads its defaults from its internal `config.json` but allows overrides from the main app settings:

```json
{
    "system_encryption": {
        "default_algorithm": "aes-256-gcm",
        "rsa_key_size": 4096,
        "hmac_algorithm": "sha256",
        "logging": {
            "log_operations": true,
            "log_key_generation": true
        }
    }
}
```

---

## 📝 Using `encryption_api` in Your Own Modules

To use the encryption capabilities in any other Massir module, simply request the `encryption_api` service from the context during the `load` phase:

```python
from massir.core.interfaces import IModule

class MyCustomModule(IModule):
    name = "my_custom_module"
    requires = ["encryption_api", "core_logger"]

    async def load(self, context):
        # 1. Retrieve the encryption service
        self.encryption = context.services.get("encryption_api")
        self.logger = context.services.get("core_logger")
        
        # 2. Generate a key and encrypt data
        key = self.encryption.generate_symmetric_key()
        encrypted_data = self.encryption.encrypt(b"Top Secret Payload", key)
        
        # 3. Decrypt data
        decrypted_bytes = self.encryption.decrypt(encrypted_data, key)
        self.logger.log(f"Decrypted: {decrypted_bytes.decode()}", tag="my_module")
```

---

## 📜 License

This example is part of the Massir project and is licensed under the **MIT License**.
