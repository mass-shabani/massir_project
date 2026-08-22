"""
Encryption Tester Module

Automatically tests all features of the system_encryption module
on startup and displays detailed results.
"""
import json
import time
from typing import Dict, List, Any
from massir.core.interfaces import IModule

class EncryptionTesterModule(IModule):
    """
    Tests all encryption operations and displays results.
    
    This module runs comprehensive tests on:
    - AES-256-GCM encryption/decryption
    - RSA-4096 key generation, encryption, signing
    - HMAC signing and verification
    - Key export/import
    - EncryptedData container serialization
    """

    def __init__(self):
        self.encryption = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._test_results: Dict[str, Any] = {}

    async def load(self, context):
        """Load module and get required services."""
        self.encryption = context.services.get('encryption_api')
        self.logger = context.services.get('core_logger')
        self.colors = context.services.get('log_colors')
        core_config = context.services.get('core_config')
        if core_config:
            self._config = core_config.get('encryption_tester', {})
        if self.logger:
            self.logger.log('EncryptionTester module loaded', tag='tester')

    async def ready(self, context):
        """Run all encryption tests. Display final results when all modules are ready."""
        if not self._config.get('run_all_tests', True):
            if self.logger:
                self.logger.log('Tests disabled in config', tag='tester')
            return
        await self._run_all_tests()

        if self._config.get('output_results', True) and self._test_results:
            await self._display_summary()

    async def stop(self, context):
        """Cleanup."""
        if self.logger:
            self.logger.log('EncryptionTester module stopped', tag='tester')

    # =========================================================================
    # Test Runner
    # =========================================================================

    async def _run_all_tests(self):
        """Run all encryption tests."""
        if self.logger:
            self._log_header('🔐 Starting Encryption Tests')
        test_categories = self._config.get('test_categories', ['aes', 'rsa', 'hmac', 'key_management', 'integration'])
        for category in test_categories:
            test_method = getattr(self, f'_test_{category}', None)
            if test_method:
                try:
                    result = await test_method()
                    self._test_results[category] = result
                except Exception as e:
                    self._test_results[category] = {'passed': False, 'error': str(e)}
                    if self.logger:
                        self.logger.print(f'❌ Test {category} FAILED: {e}', tag='tester', level='ERROR')
    
    # =========================================================================
    # AES Tests
    # =========================================================================
    
    async def _test_aes(self) -> Dict:
        """Test AES-256-GCM operations."""
        results = {'passed': True, 'subtests': []}
        if self.logger:
            self._log_header('📦 AES-256-GCM Tests')

        # Test 1: Key generation
        try:
            key = self.encryption.generate_symmetric_key()
            assert len(key) == 32, f'Key size should be 32, got {len(key)}'
            results['subtests'].append({'name': 'key_generation', 'passed': True})
            self._log_success('Key generation: 32-byte key created')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'key_generation', 'passed': False, 'error': str(e)})
            self._log_fail('Key generation', e)

        # Test 2: Basic encryption/decryption
        try:
            key = self.encryption.generate_symmetric_key()
            plaintext = b'Hello, World! This is a secret message.'
            encrypted = self.encryption.encrypt(plaintext, key)
            assert encrypted.algorithm == 'aes-256-gcm'
            assert encrypted.nonce is not None
            assert encrypted.tag is not None
            assert len(encrypted.nonce) == 12
            assert len(encrypted.tag) == 16
            decrypted = self.encryption.decrypt(encrypted, key)
            assert decrypted == plaintext, "Decrypted text doesn't match original"
            results['subtests'].append({'name': 'encrypt_decrypt', 'passed': True})
            self._log_success('Basic encryption/decryption: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'encrypt_decrypt', 'passed': False, 'error': str(e)})
            self._log_fail('Encrypt/Decrypt', e)

        # Test 3: Encryption with AAD
        try:
            key = self.encryption.generate_symmetric_key()
            plaintext = b'Secret data'
            aad = b'Additional authenticated data'
            encrypted = self.encryption.encrypt(plaintext, key, associated_data=aad)
            assert encrypted.associated_data == aad

            # Decrypt with correct AAD
            decrypted = self.encryption.decrypt(encrypted, key)
            assert decrypted == plaintext
            results['subtests'].append({'name': 'encryption_with_aad', 'passed': True})
            self._log_success('Encryption with AAD: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'encryption_with_aad', 'passed': False, 'error': str(e)})
            self._log_fail('AAD encryption', e)
                    
        # Test 4: Wrong key should fail
        try:
            key1 = self.encryption.generate_symmetric_key()
            key2 = self.encryption.generate_symmetric_key()
            plaintext = b'Secret'
            encrypted = self.encryption.encrypt(plaintext, key1)
            try:
                self.encryption.decrypt(encrypted, key2)
                # Should not reach here
                results['passed'] = False
                results['subtests'].append({'name': 'wrong_key_detection', 'passed': False})
                self._log_fail('Wrong key detection', 'Should have raised exception')
            except Exception:
                # Expected behavior
                results['subtests'].append({'name': 'wrong_key_detection', 'passed': True})
                self._log_success('Wrong key detection: Correctly raised exception')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'wrong_key_detection', 'passed': False, 'error': str(e)})
            self._log_fail('Wrong key detection', e)
                
        # Test 5: EncryptedData serialization
        try:
            key = self.encryption.generate_symmetric_key()
            plaintext = b'Serialize me!'
            encrypted = self.encryption.encrypt(plaintext, key)

            # Serialize to dict
            data_dict = encrypted.to_dict()
            assert isinstance(data_dict, dict)
            assert 'algorithm' in data_dict
            assert 'ciphertext' in data_dict

            # Serialize to JS
            json_str = json.dumps(data_dict)
            assert isinstance(json_str, str)

            # Deserialize from dict
            from massir.modules.system_encryption.core.encryption_api import EncryptedData
            restored = EncryptedData.from_dict(json.loads(json_str))

            # Decrypt with restored data
            decrypted = self.encryption.decrypt(restored, key)
            assert decrypted == plaintext
            results['subtests'].append({'name': 'serialization', 'passed': True})
            self._log_success('EncryptedData serialization: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'serialization', 'passed': False, 'error': str(e)})
            self._log_fail('Serialization', e)
        self._log_result('AES-256-GCM', results['passed'])
        return results
        
    # =========================================================================
    # RSA Tests
    # =========================================================================
    

    async def _test_rsa(self) -> Dict:
        """Test RSA-4096 operations."""
        results = {'passed': True, 'subtests': []}
        if self.logger:
            self._log_header('🔑 RSA-4096 Tests')

        # Test 1: Key generation
        try:
            public_key, private_key = self.encryption.generate_keypair()
            assert public_key is not None
            assert private_key is not None
            results['subtests'].append({'name': 'keypair_generation', 'passed': True})
            self._log_success('RSA keypair generation: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'keypair_generation', 'passed': False, 'error': str(e)})
            self._log_fail('Keypair generation', e)
            return results  # Can't continue without keys
                
        # Test 2: Encryption/Decryption
        try:
            plaintext = b'RSA encrypted message'
            ciphertext = self.encryption.encrypt_with_public(plaintext, public_key)
            assert ciphertext != plaintext
            decrypted = self.encryption.decrypt_with_private(ciphertext, private_key)
            assert decrypted == plaintext
            results['subtests'].append({'name': 'encrypt_decrypt', 'passed': True})
            self._log_success('RSA encryption/decryption: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'encrypt_decrypt', 'passed': False, 'error': str(e)})
            self._log_fail('RSA encrypt/decrypt', e)
                    
        # Test 3: Digital signatures
        try:
            data = b'Sign this document'
            signature = self.encryption.sign(data, private_key)
            assert signature is not None
            assert signature != data
                        
            # Verify with correct public key
            is_valid = self.encryption.verify(data, signature, public_key)
            assert is_valid, 'Signature should be valid'
                        
            # Verify with wrong data
            is_valid_wrong = self.encryption.verify(b'wrong data', signature, public_key)
            assert not is_valid_wrong, 'Signature should be invalid for wrong data'
            results['subtests'].append({'name': 'digital_signature', 'passed': True})
            self._log_success('RSA digital signatures: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'digital_signature', 'passed': False, 'error': str(e)})
            self._log_fail('Digital signatures', e)
                    
        # Test 4: Key export/impor
        try:
            # Export public key
            pub_bytes = self.encryption.export_public_key(public_key)
            assert pub_bytes.startswith(b'-----BEGIN PUBLIC KEY-----')
                        
            # Export private key (no password)
            priv_bytes = self.encryption.export_private_key(private_key)
            assert b'PRIVATE KEY' in priv_bytes
                        
            # Export private key (with password)
            priv_encrypted = self.encryption.export_private_key(private_key, password=b'secret123')
            assert priv_encrypted != priv_bytes
                        
            # Import back
            imported_pub = self.encryption.import_public_key(pub_bytes)
            imported_priv = self.encryption.import_private_key(priv_bytes)
            imported_priv_enc = self.encryption.import_private_key(priv_encrypted, password=b'secret123')
                        
            # Verify imported keys work
            ciphertext = self.encryption.encrypt_with_public(b'test', imported_pub)
            decrypted = self.encryption.decrypt_with_private(ciphertext, imported_priv)
            assert decrypted == b'test'
            results['subtests'].append({'name': 'key_export_import', 'passed': True})
            self._log_success('RSA key export/import: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'key_export_import', 'passed': False, 'error': str(e)})
            self._log_fail('Key export/import', e)
        self._log_result('RSA-4096', results['passed'])
        return results
        
    # =========================================================================
    # HMAC Tests
    # =========================================================================
    

    async def _test_hmac(self) -> Dict:
        """Test HMAC operations."""
        results = {'passed': True, 'subtests': []}
        if self.logger:
            self._log_header('✍️ HMAC Tests')
                    
        # Test 1: HMAC key generation
        try:
            hmac_key = self.encryption.generate_hmac_key()
            assert len(hmac_key) == 32
            hmac_key_64 = self.encryption.generate_hmac_key(64)
            assert len(hmac_key_64) == 64
            results['subtests'].append({'name': 'key_generation', 'passed': True})
            self._log_success('HMAC key generation: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'key_generation', 'passed': False, 'error': str(e)})
            self._log_fail('HMAC key generation', e)
                    
        # Test 2: HMAC creation and verification
        try:
            hmac_key = self.encryption.generate_hmac_key()
            message = b'This message must be authenticated'

            # Create HMAC
            signature = self.encryption.create_hmac(message, hmac_key)
            assert signature is not None
            assert len(signature) > 0
                        
            # Verify with correct key
            is_valid = self.encryption.verify_hmac(message, signature, hmac_key)
            assert is_valid, 'HMAC should be valid'
                        
            # Verify with wrong key
            wrong_key = self.encryption.generate_hmac_key()
            is_valid_wrong = self.encryption.verify_hmac(message, signature, wrong_key)
            assert not is_valid_wrong, 'HMAC should be invalid with wrong key'
                        
            # Verify with tampered message
            is_valid_tampered = self.encryption.verify_hmac(b'tampered message', signature, hmac_key)
            assert not is_valid_tampered, 'HMAC should be invalid for tampered message'
            results['subtests'].append({'name': 'create_verify', 'passed': True})
            self._log_success('HMAC creation and verification: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'create_verify', 'passed': False, 'error': str(e)})
            self._log_fail('HMAC create/verify', e)
                    
        # Test 3: Different algorithms
        try:
            hmac_key = self.encryption.generate_hmac_key()
            message = b'Test different algorithms'
            algorithms = ['sha256', 'sha384', 'sha512']
            signatures = {}
            for algo in algorithms:
                sig = self.encryption.create_hmac(message, hmac_key, algorithm=algo)
                signatures[algo] = sig
                                
                # Verify
                is_valid = self.encryption.verify_hmac(message, sig, hmac_key, algorithm=algo)
                assert is_valid, f'HMAC with {algo} should be valid'
                                
                # Different algorithms should produce different signatures
                for other_algo, other_sig in signatures.items():
                    if other_algo != algo:
                        assert sig != other_sig, f'{algo} and {other_algo} should produce different signatures'
            results['subtests'].append({'name': 'different_algorithms', 'passed': True})
            self._log_success('Different HMAC algorithms: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'different_algorithms', 'passed': False, 'error': str(e)})
            self._log_fail('Different algorithms', e)
        self._log_result('HMAC', results['passed'])
        return results
        
    # =========================================================================
    # Key Management Tests
    # =========================================================================
    
    async def _test_key_management(self) -> Dict:
        """Test key management operations."""
        results = {'passed': True, 'subtests': []}
        if self.logger:
            self._log_header('🗝️ Key Management Tests')

        # Test 1: Random bytes generation
        try:
            random_32 = self.encryption.generate_random_bytes(32)
            assert len(random_32) == 32
            random_64 = self.encryption.generate_random_bytes(64)
            assert len(random_64) == 64
                        
            # Should be different each time
            random_2 = self.encryption.generate_random_bytes(32)
            assert random_32 != random_2, 'Random bytes should be different'
            results['subtests'].append({'name': 'random_bytes', 'passed': True})
            self._log_success('Random bytes generation: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'random_bytes', 'passed': False, 'error': str(e)})
            self._log_fail('Random bytes', e)
                    
        # Test 2: Get info
        try:
            info = self.encryption.get_info()
            assert info['module'] == 'system_encryption'
            assert 'algorithms' in info
            assert 'key_sizes' in info
            results['subtests'].append({'name': 'get_info', 'passed': True})
            self._log_success(f"Module info: {info['algorithms']['symmetric']}, {info['algorithms']['asymmetric']}")
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'get_info', 'passed': False, 'error': str(e)})
            self._log_fail('Get info', e)
        self._log_result('Key Management', results['passed'])
        return results
    
    # =========================================================================
    # Integration Tests
    # =========================================================================
    
    async def _test_integration(self) -> Dict:
        """Test integration scenarios combining multiple operations."""
        results = {'passed': True, 'subtests': []}
        if self.logger:
            self._log_header('🔗 Integration Tests')
                    
        # Test 1: Hybrid encryption (RSA + AES)
        try:
            # Scenario: Alice wants to send encrypted message to Bob
            
            # Bob generates RSA keypair and shares public key
            bob_public, bob_private = self.encryption.generate_keypair()
                        
            # Alice generates AES session key
            session_key = self.encryption.generate_symmetric_key()
                        
            # Alice encrypts message with AES
            message = b'Hello Bob! This is a secret message from Alice.'
            encrypted_message = self.encryption.encrypt(message, session_key)
                        
            # Alice encrypts session key with Bob's public key
            encrypted_session_key = self.encryption.encrypt_with_public(session_key, bob_public)
                        
            # Alice signs the encrypted message
            signature = self.encryption.sign(encrypted_message.ciphertext, bob_private)

            # Bob receives: encrypted_session_key, encrypted_message, signature
            
            # Bob decrypts session key with his private key
            decrypted_session_key = self.encryption.decrypt_with_private(encrypted_session_key, bob_private)
            
            assert decrypted_session_key == session_key
                        
            # Bob verifies signature
            is_valid = self.encryption.verify(encrypted_message.ciphertext, signature, bob_public)
            
            # Note: In real scenario, Alice would sign with her private key
            
            # Bob decrypts message
            decrypted_message = self.encryption.decrypt(encrypted_message, decrypted_session_key)
            assert decrypted_message == message
            results['subtests'].append({'name': 'hybrid_encryption', 'passed': True})
            self._log_success('Hybrid encryption (RSA + AES): PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'hybrid_encryption', 'passed': False, 'error': str(e)})
            self._log_fail('Hybrid encryption', e)

        # Test 2: Encrypted data storage simulation
        try:
            # Simulate storing encrypted user data
            
            # Generate encryption key
            storage_key = self.encryption.generate_symmetric_key()

            # User data
            user_data = {
                'username': 'alice', 
                'email': 'alice@example.com', 
                'password_hash': 'bcrypt_hash_here', 
                'api_key': 'secret_api_key_12345'
                         }
            
            # Serialize to JSON
            user_json = json.dumps(user_data).encode()

            # Encrypt
            encrypted_user = self.encryption.encrypt(user_json, storage_key)

            # Convert to dict for storage (e.g., in database)
            stored_data = encrypted_user.to_dict()

            # Later: retrieve from storage
            retrieved_json = json.dumps(stored_data)
            retrieved_dict = json.loads(retrieved_json)
            from massir.modules.system_encryption.core.encryption_api import EncryptedData
            reconstructed = EncryptedData.from_dict(retrieved_dict)

            # Decrypt
            decrypted_json = self.encryption.decrypt(reconstructed, storage_key)
            decrypted_user = json.loads(decrypted_json.decode())
            assert decrypted_user == user_data
            results['subtests'].append({'name': 'encrypted_storage', 'passed': True})
            self._log_success('Encrypted data storage simulation: PASSED')
        except Exception as e:
            results['passed'] = False
            results['subtests'].append({'name': 'encrypted_storage', 'passed': False, 'error': str(e)})
            self._log_fail('Encrypted storage', e)
        self._log_result('Integration', results['passed'])
        return results
        
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _log_header(self, message: str):
        """Log a section header."""
        if self.logger:
            self.logger.print('', tag='tester')
            self.logger.print('=' * 50, tag='tester')
            self.logger.print(message, tag='tester', color=self.colors.BRIGHT_CYAN if self.colors else None)
            self.logger.print('=' * 50, tag='tester')

    def _log_success(self, message: str):
        """Log a success message."""
        if self.logger:
            self.logger.print(f'✅ {message}', tag='tester', color=self.colors.BRIGHT_GREEN if self.colors else None)

    def _log_fail(self, test_name: str, error: Exception):
        """Log a failure message."""
        if self.logger:
            self.logger.print(f'❌ {test_name} FAILED: {error}', tag='tester', level='ERROR')

    def _log_result(self, category: str, passed: bool):
        """Log final result for a category."""
        if self.logger:
            status = 'PASSED ✅' if passed else 'FAILED ❌'
            color = self.colors.BRIGHT_GREEN if passed else self.colors.BRIGHT_RED
            self.logger.print(f"\n{'=' * 30}\n{category}: {status}\n{'=' * 30}", tag='tester', color=color if self.colors else None)

    async def _display_summary(self):
        """Display summary of all tests."""
        if self.logger:
            self.logger.print('', tag='tester')
            self.logger.print('=' * 60, tag='tester')
            total = len(self._test_results)
            passed = sum((1 for r in self._test_results.values() if r.get('passed', False)))
            failed = total - passed
            self.logger.print(f'📊 Test Summary: {passed}/{total} categories passed', tag='tester', color=self.colors.BRIGHT_YELLOW if self.colors else None)
            for category, result in self._test_results.items():
                status = '✅ PASSED' if result.get('passed') else '❌ FAILED'
                subtests = result.get('subtests', [])
                sub_passed = sum((1 for s in subtests if s.get('passed', False)))
                self.logger.print(f'  {category}: {status} ({sub_passed}/{len(subtests)} subtests)', tag='tester')
            if failed == 0:
                self.logger.print('\n🎉 All encryption tests completed successfully!', tag='tester', color=self.colors.BRIGHT_GREEN if self.colors else None)
            else:
                self.logger.print(f'\n⚠️ {failed} test category(ies) failed. Check logs above.', tag='tester', level='WARNING')
            self.logger.print('=' * 60, tag='tester')