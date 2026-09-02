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

    def __init__(self):
        self.encryption = None
        self.logger = None
        self._config: Dict = {}
        self._master_key: Optional[bytes] = None

    async def start(self, context):
        """Load services, initialize encryption, register service, and run demo if configured."""
        self.encryption = context.services.get('encryption_api')
        self.logger = context.services.get('core_logger')
        encryption_types = context.services.get('encryption_types') or {}
        self._encrypted_data_cls = encryption_types.get('EncryptedData')

        core_config = context.services.get('core_config')
        if core_config:
            self._config = core_config.get('encryption_demo', {})

        self._master_key = self.encryption.generate_symmetric_key()

        context.services.set('encryption_service', self)
        if self.logger:
            self.logger.log('EncryptionDemo module started - encryption_service available', tag='demo')

        if self._config.get('auto_test_on_start', False):
            await self._run_demo()

    async def stop(self, context):
        """Cleanup - clear master key."""
        self._master_key = None
        if self.logger:
            self.logger.log('EncryptionDemo module stopped', tag='demo')
                
    # =========================================================================
    # Public Service Methods
    # =========================================================================
    
    def encrypt_string(self, text: str) -> Dict[str, Any]:
        plaintext = text.encode('utf-8')
        encrypted = self.encryption.encrypt(plaintext, self._master_key)
        return encrypted.to_dict()

    def decrypt_string(self, encrypted_data: Dict[str, Any]) -> str:
        encrypted = self._encrypted_data_cls.from_dict(encrypted_data)
        plaintext = self.encryption.decrypt(encrypted, self._master_key)
        return plaintext.decode('utf-8')

    def encrypt_dict(self, data: Dict) -> Dict[str, Any]:
        json_bytes = json.dumps(data).encode('utf-8')
        encrypted = self.encryption.encrypt(json_bytes, self._master_key)
        return encrypted.to_dict()

    def decrypt_dict(self, encrypted_data: Dict[str, Any]) -> Dict:
        encrypted = self._encrypted_data_cls.from_dict(encrypted_data)
        json_bytes = self.encryption.decrypt(encrypted, self._master_key)
        return json.loads(json_bytes.decode('utf-8'))

    def sign_message(self, message: str) -> Dict[str, Any]:
        public_key, private_key = self.encryption.generate_keypair()
        message_bytes = message.encode('utf-8')
        signature = self.encryption.sign(message_bytes, private_key)
        return {'message': message, 'signature': signature.hex(), 'public_key': self.encryption.export_public_key(public_key).decode('utf-8')}

    def verify_message(self, signed_data: Dict[str, Any]) -> bool:
        message_bytes = signed_data['message'].encode('utf-8')
        signature = bytes.fromhex(signed_data['signature'])
        public_key = self.encryption.import_public_key(signed_data['public_key'].encode('utf-8'))
        return self.encryption.verify(message_bytes, signature, public_key)

    def create_hmac(self, data: str) -> Dict[str, Any]:
        hmac_key = self._master_key
        data_bytes = data.encode('utf-8')
        signature = self.encryption.create_hmac(data_bytes, hmac_key)
        return {'data': data, 'hmac': signature.hex(), 'algorithm': 'sha256'}

    def verify_hmac(self, hmac_data: Dict[str, Any]) -> bool:
        data_bytes = hmac_data['data'].encode('utf-8')
        signature = bytes.fromhex(hmac_data['hmac'])
        algorithm = hmac_data.get('algorithm', 'sha256')
        return self.encryption.verify_hmac(data_bytes, signature, self._master_key, algorithm)
        
    # =========================================================================
    # Demo Method
    # =========================================================================
    
    async def _run_demo(self):
        """Run a demonstration of encryption features."""
        if not self.logger:
            return
        self.logger.print('', tag='demo')
        self.logger.print('=' * 50, tag='demo')
        self.logger.print('🎬 Running Encryption Demo', tag='demo')
        self.logger.print('=' * 50, tag='demo')

        test_data = self._config.get('test_data', {})
        sample_message = test_data.get('sample_message', 'Hello, this is a secret message!')
        self.logger.print(f'\n📝 Original message: {sample_message}', tag='demo')
        encrypted = self.encrypt_string(sample_message)
        self.logger.print(f"🔒 Encrypted: {encrypted['ciphertext'][:32]}...", tag='demo')
        decrypted = self.decrypt_string(encrypted)
        self.logger.print(f'🔓 Decrypted: {decrypted}', tag='demo')
        assert decrypted == sample_message
        self.logger.print('✅ String encryption/decryption: SUCCESS', tag='demo')

        sample_json = test_data.get('sample_json', {'user': 'alice', 'action': 'login'})
        self.logger.print(f'\n📦 Original dict: {sample_json}', tag='demo')
        encrypted_dict = self.encrypt_dict(sample_json)
        decrypted_dict = self.decrypt_dict(encrypted_dict)
        self.logger.print(f'🔓 Decrypted dict: {decrypted_dict}', tag='demo')
        assert decrypted_dict == sample_json
        self.logger.print('✅ Dictionary encryption/decryption: SUCCESS', tag='demo')

        message_to_sign = 'This message is digitally signed'
        signed = self.sign_message(message_to_sign)
        self.logger.print(f'\n✍️ Signed message: {message_to_sign}', tag='demo')
        self.logger.print(f"🔏 Signature: {signed['signature'][:32]}...", tag='demo')
        is_valid = self.verify_message(signed)
        self.logger.print(f'✅ Signature valid: {is_valid}', tag='demo')

        data_to_auth = 'Authenticate this data'
        hmac_result = self.create_hmac(data_to_auth)
        self.logger.print(f'\n🏷️ HMAC data: {data_to_auth}', tag='demo')
        self.logger.print(f"🔐 HMAC: {hmac_result['hmac'][:32]}...", tag='demo')
        is_valid_hmac = self.verify_hmac(hmac_result)
        self.logger.print(f'✅ HMAC valid: {is_valid_hmac}', tag='demo')
        self.logger.print('\n' + '=' * 50, tag='demo')
        self.logger.print('🎉 Demo completed successfully!', tag='demo')
        self.logger.print('=' * 50, tag='demo')
