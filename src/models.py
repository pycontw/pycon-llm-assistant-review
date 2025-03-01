from pydantic import BaseModel
from typing import Literal, Dict, Any, Optional

class ProposalReview(BaseModel):
    """Review for a PyCon proposal"""
    summary: str
    comment: str
    vote: Literal['+1', '+0', '-0', '-1']
    proposal_id: Optional[str] = None

class VoteStats(BaseModel):
    """Statistics for votes on a proposal"""
    proposal_id: str
    most_common_vote: str
    vote_counts: Dict[str, int]
    mean: float
    std: float
    count: int
    median: float 