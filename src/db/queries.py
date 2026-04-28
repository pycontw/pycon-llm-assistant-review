# SQL queries for Metabase database operations

# Query 1: Get proposals for specific conference
GET_PROPOSALS_BY_CONF = """
SELECT 
    CAST(p.id AS VARCHAR) AS proposal_id,
    p.title,
    p.abstract,
    p.detailed_description,
    p.outline,
    p.objective,
    p.conference
FROM proposals_talkproposal p
WHERE 1=1
  and p.conference = {{conference}}
  and p.cancelled = FALSE
"""

# Query 2: Get proposals with negative reviews, excluding specific conferences
GET_NEGATIVE_PROPOSALS = """
WITH proposal_stats AS (
    SELECT 
        CAST(p.id AS VARCHAR) AS proposal_id,
        p.conference,
        p.title,
        p.abstract,
        p.detailed_description,
        p.outline,
        p.objective,
        COUNT(CASE WHEN r.vote = '-1' THEN 1 END) AS negative_votes,
        COUNT(*) AS total_reviews,
        ROUND(100.0 * COUNT(CASE WHEN r.vote = '-1' THEN 1 END) / COUNT(*), 2) AS negative_percentage
    FROM proposals_talkproposal p
    LEFT JOIN reviews_review r ON p.id = r.proposal_id
    WHERE 1=1
      and p.conference != {{exclude_conference}}
      and p.cancelled = FALSE
    GROUP BY p.id, p.conference, p.title, p.abstract, p.detailed_description, p.outline, p.objective
    HAVING COUNT(*) >= {{min_reviews}}
)
SELECT *
FROM proposal_stats
WHERE negative_percentage >= {{negative_threshold}}
"""

# Query 3: Get all reviews by proposal_id
GET_REVIEWS_BY_PROPOSAL = """
SELECT 
    CAST(r.id AS VARCHAR) AS review_id,
    CAST(r.proposal_id AS VARCHAR) AS proposal_id,
    r.vote,
    r.comment
FROM reviews_review r
WHERE r.proposal_id IN {{proposal_ids}}
ORDER BY r.proposal_id, r.id
""" 