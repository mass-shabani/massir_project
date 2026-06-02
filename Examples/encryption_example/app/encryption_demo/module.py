"""
Encryption Demo Module

Provides a service layer for encryption operations that can be
used by other modules in the application.
"""

import json
from typing import Dict, Any, Optional

from massir.core.interfaces import IModule


class EncryptionDemoModule(IModule):
    """
    Provides encryption_service for other modules.
    
    This module wraps the encryption_api with higher-level
    operations suitable for application use.
    """
    
    name = "encryption_demo"
    
    def __init__(self):
        self.encryption = None
        self.logger = None
        self._config: Dict = {}
        self._master_key: Optional[bytes] = None
    
    async def load(self, context):
        """Load module and initialize services."""
        self.encryption = context.services.get("encryption_api")
        self.logger = context.services.get("core_logger")
        
        # Load configuration
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("encryption_demo", {})
        
        # Generate master key for this session
        self._master_key = self.encryption.generate_symmetric_key()
        
        # Register the service
        context.services.set("encryption_service", self)
        
        if self.logger:
            self.logger.log(
                "EncryptionDemo module loaded - encryption_service available",
                tag="demo"
            )
    
    async def start(self, context):
        """Run auto-test if configured."""
        if self._config.get("auto_test_on_start", False):
            await self._run_demo()
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log(
                "EncryptionDemo module ready",
                tag="demo"
            )
    
    async def stop(self, context):
        """Cleanup - clear master key."""
        self._master_key = None
        if self.logger:
            self.logger.log("EncryptionDemo module stopped", tag="demo")
    
    # =========================================================================
    # Public Service Methods
    # =========================================================================
    
    def encrypt_string(self, text: str) -> Dict[str, Any]:
        """
        Encrypt a string and return serializable result.
        
        Args:
            text: String to encrypt
            
        Returns:
            Dictionary containing encrypted data (JSON serializable)
        """
        plaintext = text.encode("utf-8")
        encrypted = self.encryption.encrypt(plaintext, self._master_key)
        return encrypted.to_dict()
    
    def decrypt_string(self, encrypted_data: Dict[str, Any]) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_data: Dictionary from encrypt_string()
            
        Returns:
            Decrypted string
        """
        from massir.modules.system_encryption.core.encryption_api import EncryptedData
        
        encrypted = EncryptedData.from_dict(encrypted_data)
        plaintext = self.encryption.decrypt(encrypted, self._master_key)
        return plaintext.decode("utf-8")
    
    def encrypt_dict(self, data: Dict) -> Dict[str, Any]:
        """
        Encrypt a dictionary (JSON serializable).
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Dictionary containing encrypted data
        """
        json_bytes = json.dumps(data).encode("utf-8")
        encrypted = self.encryption.encrypt(json_bytes, self._master_key)
        return encrypted.to_dict()
    
    def decrypt_dict(self, encrypted_data: Dict[str, Any]) -> Dict:
        """
        Decrypt an encrypted dictionary.
        
        Args:
            encrypted_data: Dictionary from encrypt_dict()
            
        Returns:
            Original dictionary
        """
        from massir.modules.system_encryption.core.encryption_api import EncryptedData
        
        encrypted = EncryptedData.from_dict(encrypted_data)
        json_bytes = self.encryption.decrypt(encrypted, self._master_key)
        return json.loads(json_bytes.decode("utf-8"))
    
    def sign_message(self, message: str) -> Dict[str, Any]:
        """
        Create a signed message using RSA.
        
        Args:
            message: Message to sign
            
        Returns:
            Dictionary with message and signature
        """
        # Generate ephemeral keypair for signing
        public_key, private_key = self.encryption.generate_keypair()
        
        message_bytes = message.encode("utf-8")
        signature = self.encryption.sign(message_bytes, private_key)
        
        return {
            "message": message,
            "signature": signature.hex(),
            "public_key": self.encryption.export_public_key(public_key).decode("utf-8")
        }
    
    def verify_message(self, signed_data: Dict[str, Any]) -> bool:
        """
        Verify a signed message.
        
        Args:
            signed_data: Dictionary from sign_message()
            
        Returns:
            True if signature is valid
        """
        message_bytes = signed_data["message"].encode("utf-8")
        signature = bytes.fromhex(signed_data["signature"])
        public_key = self.encryption.import_public_key(
            signed_data["public_key"].encode("utf-8")
        )
        
        return self.encryption.verify(message_bytes, signature, public_key)
    
    def create_hmac(self, data: str) -> Dict[str, Any]:
        """
        Create HMAC for data authentication.
        
        Args:
            data: Data to authenticate
            
        Returns:
            Dictionary with data and HMAC
        """
        hmac_key = self._master_key  # Use master key for HMAC
        data_bytes = data.encode("utf-8")
        
        signature = self.encryption.create_hmac(data_bytes, hmac_key)
        
        return {
            "data": data,
            "hmac": signature.hex(),
            "algorithm": "sha256"
        }
    
    def verify_hmac(self, hmac_data: Dict[str, Any]) -> bool:
        """
        Verify HMAC authentication.
        
        Args:
            hmac_data: Dictionary from create_hmac()
            
        Returns:
            True if HMAC is valid
        """
        data_bytes = hmac_data["data"].encode("utf-8")
        signature = bytes.fromhex(hmac_data["hmac"])
        algorithm = hmac_data.get("algorithm", "sha256")
        
        return self.encryption.verify_hmac(
            data_bytes, signature, self._master_key, algorithm
        )
    
    # =========================================================================
    # Demo Method
    # =========================================================================
    
    async def _run_demo(self):
        """Run a demonstration of encryption features."""
        if not self.logger:
            return
        
        self.logger.log("", tag="demo")
        self.logger.log("=" * 50, tag="demo")
        self.logger.log("🎬 Running Encryption Demo", tag="demo")
        self.logger.log("=" * 50, tag="demo")
        
        # Demo 1: String encryption
        test_data = self._config.get("test_data", {})
        sample_message = test_data.get(
            "sample_message",
            "Hello, this is a secret message!"
        )
        
        self.logger.log(f"\n📝 Original message: {sample_message}", tag="demo")
        
        encrypted = self.encrypt_string(sample_message)
        self.logger.log(f"🔒 Encrypted: {encrypted['ciphertext'][:32]}...", tag="demo")
        
        decrypted = self.decrypt_string(encrypted)
        self.logger.log(f"🔓 Decrypted: {decrypted}", tag="demo")
        
        assert decrypted == sample_message
        self.logger.log("✅ String encryption/decryption: SUCCESS", tag="demo")
        
        # Demo 2: Dictionary encryption
        sample_json = test_data.get(
            "sample_json",
            {"user": "alice", "action": "login"}
        )
        
        self.logger.log(f"\n📦 Original dict: {sample_json}", tag="demo")
        
        encrypted_dict = self.encrypt_dict(sample_json)
        decrypted_dict = self.decrypt_dict(encrypted_dict)
        
        self.logger.log(f"🔓 Decrypted dict: {decrypted_dict}", tag="demo")
        assert decrypted_dict == sample_json
        self.logger.log("✅ Dictionary encryption/decryption: SUCCESS", tag="demo")
        
        # Demo 3: Digital signature
        message_to_sign = "This message is digitally signed"
        signed = self.sign_message(message_to_sign)
        
        self.logger.log(f"\n✍️ Signed message: {message_to_sign}", tag="demo")
        self.logger.log(f"🔏 Signature: {signed['signature'][:32]}...", tag="demo")
        
        is_valid = self.verify_message(signed)
        self.logger.log(f"✅ Signature valid: {is_valid}", tag="demo")
        
        # Demo 4: HMAC
        data_to_auth = "Authenticate this data"
        hmac_result = self.create_hmac(data_to_auth)
        
        self.logger.log(f"\n🏷️ HMAC data: {data_to_auth}", tag="demo")
        self.logger.log(f"🔐 HMAC: {hmac_result['hmac'][:32]}...", tag="demo")
        
        is_valid_hmac = self.verify_hmac(hmac_result)
        self.logger.log(f"✅ HMAC valid: {is_valid_hmac}", tag="demo")
        
        self.logger.log("\n" + "=" * 50, tag="demo")
        self.logger.log("🎉 Demo completed successfully!", tag="demo")
        self.logger.log("=" * 50, tag="demo")