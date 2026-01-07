import random
import string


def generate_voter_id(user_model):
    """
    Generate unique 10-character random Voter ID
    Format: Uppercase letters and numbers only (no dashes)
    Example: A7K9X2M5B3, P4Q8R6T2Y9, X3N7M9K4L8
    
    Args:
        user_model: SQLAlchemy User model to check for uniqueness
    
    Returns:
        str: Unique 10-character voter ID
    """
    while True:
        # Generate 10 random characters (uppercase letters and digits)
        voter_id = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )
        
        # Ensure uniqueness - check if this ID already exists
        if not user_model.query.filter_by(voter_id=voter_id).first():
            return voter_id


def validate_voter_id_format(voter_id):
    """
    Validate Voter ID format
    Must be exactly 10 characters, uppercase letters and digits only
    
    Args:
        voter_id: String to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    if not voter_id or len(voter_id) != 10:
        return False
    
    # Check if all characters are uppercase letters or digits
    return all(c in string.ascii_uppercase + string.digits for c in voter_id)


def format_voter_id_display(voter_id):
    """
    Format voter ID for display (add spaces for readability)
    Example: A7K9X2M5B3 -> A7K9 X2M5 B3
    
    Args:
        voter_id: 10-character voter ID
    
    Returns:
        str: Formatted voter ID with spaces
    """
    if len(voter_id) != 10:
        return voter_id
    
    # Split into groups of 4, 4, 2 for readability
    return f"{voter_id[:4]} {voter_id[4:8]} {voter_id[8:]}"


# Legacy functions (kept for backward compatibility)
def generate_sequential_voter_id(user_model):
    """
    DEPRECATED: Generate sequential Voter ID
    Format: VID-YEAR-XXXXXX
    Example: VID-2026-001234
    
    Note: This is kept for backward compatibility only.
    Use generate_voter_id() for new implementations.
    
    Args:
        user_model: SQLAlchemy User model to check for uniqueness
    
    Returns:
        str: Unique voter ID
    """
    from datetime import datetime
    
    year = datetime.now().year
    
    # Get the count of existing users to generate sequential number
    user_count = user_model.query.count()
    sequential_number = str(user_count + 1).zfill(6)  # Pad with zeros
    
    voter_id = f"VID-{year}-{sequential_number}"
    
    # Ensure uniqueness (rare collision case)
    while user_model.query.filter_by(voter_id=voter_id).first():
        random_suffix = ''.join(random.choices(string.digits, k=6))
        voter_id = f"VID-{year}-{random_suffix}"
    
    return voter_id