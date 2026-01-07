"""
Blockchain Service for Vote Recording
Uses Polygon (Matic) for low-cost, fast, transparent vote recording
"""

from web3 import Web3
from eth_account import Account
import hashlib
import json
from datetime import datetime
from flask import current_app
from cryptography.fernet import Fernet
import os
import time


class BlockchainService:
    """
    Handle blockchain operations for vote immutability and transparency
    
    Stores votes on Polygon blockchain for:
    - Immutability (can't change votes)
    - Transparency (anyone can verify)
    - Audit trail (complete history)
    """
    
    def __init__(self):
        self.w3 = None
        self.contract = None
        self.account = None
        self.contract_address = None
        self._initialized = False
        self.encryption_key = None
    
    def initialize(self):
        """Initialize blockchain connection"""
        try:
            # Get configuration
            blockchain_enabled = current_app.config.get('BLOCKCHAIN_ENABLED', False)
            
            if not blockchain_enabled:
                print("[BLOCKCHAIN] Blockchain disabled in config")
                return False
            
            # Connect to Polygon (Mumbai testnet for development, Mainnet for production)
            rpc_url = current_app.config.get('BLOCKCHAIN_RPC_URL')
            
            if not rpc_url:
                print("[BLOCKCHAIN] No RPC URL configured")
                return False
            
            # Connect to blockchain
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not self.w3.is_connected():
                print("[BLOCKCHAIN] Failed to connect to blockchain")
                return False
            
            # Load account from private key
            private_key = current_app.config.get('BLOCKCHAIN_PRIVATE_KEY')
            if private_key:
                self.account = Account.from_key(private_key)
                print(f"[BLOCKCHAIN] Connected with account: {self.account.address}")
            
            # Load smart contract
            contract_address = current_app.config.get('BLOCKCHAIN_CONTRACT_ADDRESS')
            contract_abi = current_app.config.get('BLOCKCHAIN_CONTRACT_ABI')
            
            if contract_address and contract_abi:
                self.contract_address = Web3.to_checksum_address(contract_address)
                self.contract = self.w3.eth.contract(
                    address=self.contract_address,
                    abi=json.loads(contract_abi)
                )
                print(f"[BLOCKCHAIN] Contract loaded at: {self.contract_address}")
            
            # Load encryption key for vote data
            encryption_key = current_app.config.get('VOTE_ENCRYPTION_KEY')
            if encryption_key:
                self.encryption_key = encryption_key.encode()
            else:
                # Generate a key if not provided (for development)
                self.encryption_key = Fernet.generate_key()
                print("[BLOCKCHAIN] WARNING: Using generated encryption key (development only)")
            
            self._initialized = True
            print("[BLOCKCHAIN] Initialization complete")
            return True
            
        except Exception as e:
            print(f"[BLOCKCHAIN] Initialization error: {str(e)}")
            return False
    
    def is_enabled(self):
        """Check if blockchain is enabled and initialized"""
        return self._initialized and current_app.config.get('BLOCKCHAIN_ENABLED', False)
    
    def create_vote_hash(self, vote_data):
        """
        Create a unique hash for a vote
        This hash proves the vote existed at a specific time
        """
        # Combine vote details into a string
        vote_string = f"{vote_data['election_id']}{vote_data['position_id']}{vote_data['candidate_id']}{vote_data['timestamp']}{vote_data.get('voter_anonymous_id', '')}"
        
        # Create SHA-256 hash
        vote_hash = hashlib.sha256(vote_string.encode()).hexdigest()
        
        return vote_hash
    
    def encrypt_vote_data(self, candidate_id):
        """
        Encrypt the candidate_id so it's not readable on blockchain
        Only decryptable by election administrators
        """
        if not self.encryption_key:
            return None
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted = fernet.encrypt(str(candidate_id).encode())
            return encrypted.hex()  # Convert to hex string for storage
        except Exception as e:
            print(f"[BLOCKCHAIN] Encryption error: {str(e)}")
            return None
    
    def decrypt_vote_data(self, encrypted_data):
        """
        Decrypt vote data (admin only operation)
        """
        if not self.encryption_key:
            return None
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_bytes = bytes.fromhex(encrypted_data)
            decrypted = fernet.decrypt(encrypted_bytes)
            return int(decrypted.decode())
        except Exception as e:
            print(f"[BLOCKCHAIN] Decryption error: {str(e)}")
            return None
    
    def create_anonymous_voter_id(self, voter_id, election_id):
        """
        Create anonymous voter ID for blockchain
        One-way hash - can't reverse to find real voter
        """
        # Add salt from config for extra security
        salt = current_app.config.get('VOTER_ID_SALT', 'default_salt')
        
        # Create hash
        data = f"{voter_id}{election_id}{salt}"
        anonymous_id = hashlib.sha256(data.encode()).hexdigest()
        
        return f"anon_{anonymous_id[:16]}"
    
    def record_vote_on_blockchain(self, vote_data):
        """
        Record a vote on the blockchain
        
        Args:
            vote_data: dict with keys:
                - election_id
                - position_id
                - candidate_id
                - voter_id (for creating anonymous ID)
                - timestamp
                - biometric_verified
                - verification_method
        
        Returns:
            dict with transaction_hash and block_number, or None if failed
        """
        if not self.is_enabled():
            print("[BLOCKCHAIN] Blockchain not enabled, skipping")
            return None
        
        try:
            # Create anonymous voter ID
            anonymous_voter_id = self.create_anonymous_voter_id(
                vote_data['voter_id'],
                vote_data['election_id']
            )
            
            # Encrypt the actual vote (candidate_id)
            encrypted_vote = self.encrypt_vote_data(vote_data['candidate_id'])
            
            # Create vote hash
            vote_hash = self.create_vote_hash({
                'election_id': vote_data['election_id'],
                'position_id': vote_data['position_id'],
                'candidate_id': vote_data['candidate_id'],
                'timestamp': vote_data['timestamp'].isoformat(),
                'voter_anonymous_id': anonymous_voter_id
            })
            
            # If smart contract is available, use it
            if self.contract and self.account:
                return self._record_with_contract(
                    vote_data,
                    anonymous_voter_id,
                    encrypted_vote,
                    vote_hash
                )
            else:
                # Fallback: direct transaction with vote data
                return self._record_direct_transaction(
                    vote_data,
                    anonymous_voter_id,
                    encrypted_vote,
                    vote_hash
                )
                
        except Exception as e:
            print(f"[BLOCKCHAIN] Record vote error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _record_with_contract(self, vote_data, anonymous_voter_id, encrypted_vote, vote_hash):
        """Record vote using smart contract"""
        try:
            # Build transaction
            transaction = self.contract.functions.recordVote(
                vote_data['election_id'],
                vote_data['position_id'],
                vote_hash,
                encrypted_vote or "0x",
                anonymous_voter_id,
                vote_data.get('biometric_verified', False),
                vote_data.get('verification_method', 'password')
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=self.account.key
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt (with timeout)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            print(f"[BLOCKCHAIN] Vote recorded in block {receipt['blockNumber']}")
            
            return {
                'transaction_hash': receipt['transactionHash'].hex(),
                'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed'],
                'status': 'success' if receipt['status'] == 1 else 'failed'
            }
            
        except Exception as e:
            print(f"[BLOCKCHAIN] Contract transaction error: {str(e)}")
            return None
    
    def _record_direct_transaction(self, vote_data, anonymous_voter_id, encrypted_vote, vote_hash):
        """Record vote as direct transaction (fallback if no contract)"""
        try:
            # Create transaction with vote data in input field
            vote_record = {
                'election_id': vote_data['election_id'],
                'position_id': vote_data['position_id'],
                'vote_hash': vote_hash,
                'encrypted_vote': encrypted_vote,
                'anonymous_voter_id': anonymous_voter_id,
                'timestamp': vote_data['timestamp'].isoformat(),
                'biometric_verified': vote_data.get('biometric_verified', False),
                'verification_method': vote_data.get('verification_method', 'password')
            }
            
            # Encode data
            data = '0x' + json.dumps(vote_record).encode().hex()
            
            # Build transaction
            transaction = {
                'from': self.account.address,
                'to': self.account.address,  # Send to self with data
                'value': 0,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'data': data
            }
            
            # Sign and send
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=self.account.key
            )
            
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            print(f"[BLOCKCHAIN] Vote recorded in block {receipt['blockNumber']}")
            
            return {
                'transaction_hash': receipt['transactionHash'].hex(),
                'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed'],
                'status': 'success' if receipt['status'] == 1 else 'failed'
            }
            
        except Exception as e:
            print(f"[BLOCKCHAIN] Direct transaction error: {str(e)}")
            return None
    
    def verify_vote_on_blockchain(self, transaction_hash):
        """
        Verify a vote exists on blockchain
        Returns vote data if found
        """
        if not self.is_enabled():
            return None
        
        try:
            # Get transaction
            tx = self.w3.eth.get_transaction(transaction_hash)
            
            if not tx:
                return None
            
            # Get transaction receipt
            receipt = self.w3.eth.get_transaction_receipt(transaction_hash)
            
            return {
                'transaction_hash': transaction_hash,
                'block_number': receipt['blockNumber'],
                'timestamp': self.w3.eth.get_block(receipt['blockNumber'])['timestamp'],
                'status': 'confirmed' if receipt['status'] == 1 else 'failed',
                'gas_used': receipt['gasUsed']
            }
            
        except Exception as e:
            print(f"[BLOCKCHAIN] Verify error: {str(e)}")
            return None
    
    def get_election_votes_from_blockchain(self, election_id):
        """
        Get all votes for an election from blockchain
        Useful for independent verification
        """
        if not self.is_enabled() or not self.contract:
            return None
        
        try:
            # Call contract to get vote count
            vote_count = self.contract.functions.getElectionVoteCount(election_id).call()
            
            return {
                'election_id': election_id,
                'total_votes': vote_count,
                'verified_on_blockchain': True
            }
            
        except Exception as e:
            print(f"[BLOCKCHAIN] Get votes error: {str(e)}")
            return None


# Singleton instance
blockchain_service = BlockchainService()