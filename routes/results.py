from flask import Blueprint, request, jsonify
from models import Election, Position, Candidate, Vote
from services.blockchain_service import blockchain_service
from extensions import db

results_bp = Blueprint('results', __name__, url_prefix='/api')


@results_bp.route('/results/<int:election_id>', methods=['GET'])
def get_results(election_id):
    """Get election results with blockchain verification"""
    try:
        election = Election.query.get_or_404(election_id)
        
        results = []
        total_votes_on_blockchain = 0
        total_votes_in_database = 0
        
        for position in election.positions:
            candidates_results = []
            for candidate in position.candidates:
                # Count votes in database (only non-flagged)
                vote_count = Vote.query.filter_by(
                    candidate_id=candidate.id,
                    is_flagged=False
                ).count()
                
                # Count votes recorded on blockchain
                blockchain_count = Vote.query.filter_by(
                    candidate_id=candidate.id,
                    is_flagged=False
                ).filter(
                    Vote.blockchain_tx_hash.isnot(None)
                ).count()
                
                total_votes_in_database += vote_count
                total_votes_on_blockchain += blockchain_count
                
                candidates_results.append({
                    'id': candidate.id,
                    'name': candidate.name,
                    'party': candidate.party,
                    'votes': vote_count,
                    'blockchain_verified_votes': blockchain_count
                })
            
            # Sort by votes
            candidates_results.sort(key=lambda x: x['votes'], reverse=True)
            
            results.append({
                'position': position.title,
                'position_id': position.id,
                'candidates': candidates_results
            })
        
        # Get blockchain verification status
        blockchain_verification = None
        if blockchain_service.is_enabled():
            blockchain_data = blockchain_service.get_election_votes_from_blockchain(election_id)
            if blockchain_data:
                blockchain_verification = {
                    'verified': True,
                    'total_votes_on_chain': blockchain_data.get('total_votes', 0),
                    'matches_database': blockchain_data.get('total_votes', 0) == total_votes_in_database
                }
        
        return jsonify({
            'election': election.title,
            'election_id': election.id,
            'results': results,
            'verification': {
                'total_votes_database': total_votes_in_database,
                'total_votes_blockchain': total_votes_on_blockchain,
                'blockchain_enabled': blockchain_service.is_enabled(),
                'blockchain_verification': blockchain_verification
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@results_bp.route('/results/<int:election_id>/summary', methods=['GET'])
def get_results_summary(election_id):
    """Get election results summary with statistics and blockchain info"""
    try:
        election = Election.query.get_or_404(election_id)
        
        total_votes = Vote.query.filter_by(
            election_id=election_id,
            is_flagged=False
        ).count()
        
        total_flagged = Vote.query.filter_by(
            election_id=election_id,
            is_flagged=True
        ).count()
        
        # Get unique voters
        unique_voters = db.session.query(Vote.user_id).filter_by(
            election_id=election_id
        ).distinct().count()
        
        # Count biometric verified votes
        biometric_votes = Vote.query.filter_by(
            election_id=election_id,
            biometric_verified=True,
            is_flagged=False
        ).count()
        
        # Count blockchain recorded votes
        blockchain_votes = Vote.query.filter_by(
            election_id=election_id,
            is_flagged=False
        ).filter(
            Vote.blockchain_tx_hash.isnot(None)
        ).count()
        
        # Calculate blockchain recording percentage
        blockchain_percentage = (blockchain_votes / total_votes * 100) if total_votes > 0 else 0
        
        return jsonify({
            'election': election.title,
            'election_id': election.id,
            'summary': {
                'total_votes': total_votes,
                'total_flagged': total_flagged,
                'unique_voters': unique_voters,
                'positions_count': len(election.positions),
                'biometric_verified_votes': biometric_votes,
                'blockchain_recorded_votes': blockchain_votes,
                'blockchain_recording_percentage': round(blockchain_percentage, 2)
            },
            'security': {
                'biometric_verification_rate': round((biometric_votes / total_votes * 100), 2) if total_votes > 0 else 0,
                'blockchain_enabled': blockchain_service.is_enabled(),
                'blockchain_recording_rate': round(blockchain_percentage, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@results_bp.route('/results/<int:election_id>/blockchain-stats', methods=['GET'])
def get_blockchain_stats(election_id):
    """Get detailed blockchain statistics for an election"""
    try:
        if not blockchain_service.is_enabled():
            return jsonify({
                'enabled': False,
                'message': 'Blockchain recording is not enabled'
            }), 200
        
        election = Election.query.get_or_404(election_id)
        
        # Get all votes with blockchain data
        votes_with_blockchain = Vote.query.filter_by(
            election_id=election_id,
            is_flagged=False
        ).filter(
            Vote.blockchain_tx_hash.isnot(None)
        ).all()
        
        # Calculate statistics
        total_votes = Vote.query.filter_by(
            election_id=election_id,
            is_flagged=False
        ).count()
        
        blockchain_stats = {
            'enabled': True,
            'election_id': election_id,
            'election_title': election.title,
            'total_votes': total_votes,
            'blockchain_recorded': len(votes_with_blockchain),
            'pending': total_votes - len(votes_with_blockchain),
            'percentage_on_chain': round((len(votes_with_blockchain) / total_votes * 100), 2) if total_votes > 0 else 0,
            'recent_transactions': []
        }
        
        # Add recent transactions (last 10)
        for vote in votes_with_blockchain[-10:]:
            blockchain_stats['recent_transactions'].append({
                'vote_id': vote.id,
                'transaction_hash': vote.blockchain_tx_hash,
                'block_number': vote.blockchain_block_number,
                'recorded_at': vote.blockchain_recorded_at.isoformat() if vote.blockchain_recorded_at else None,
                'explorer_url': vote.get_blockchain_explorer_url(),
                'biometric_verified': vote.biometric_verified
            })
        
        return jsonify(blockchain_stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500