"""
CPU Name Matching Engine
Fuzzy matching for correlating CPU names across different data sources
Uses multiple strategies for high accuracy matching
"""
import re
from typing import Optional, List, Tuple, Dict
from difflib import SequenceMatcher
import logging


class CpuMatcher:
    """
    CPU name matching engine with:
    - Name normalization
    - Multiple matching strategies
    - Confidence scoring
    - Manual override support
    """
    
    # Manufacturer prefixes to strip
    MANUFACTURER_PREFIXES = [
        r"^AMD\s+",
        r"^Intel\s+",
        r"^Intel\(R\)\s+",
        r"^AMD\(R\)\s+",
    ]
    
    # Common suffixes to normalize
    SUFFIX_PATTERNS = {
        r"\s+Processor$": "",
        r"\s+CPU$": "",
        r"\s+\d+-Core\s+Processor$": "",
        r"\s+@ [\d.]+\s*GHz$": "",
        r"\s+with Radeon.*$": "",
    }
    
    # Model number patterns
    MODEL_PATTERNS = {
        "ryzen": r"Ryzen\s+(\d+)?\s*(\d{4}\w*)",
        "core": r"Core\s+(i\d|Ultra\s+\d)[-\s]*(\d{4,5}\w*)",
        "xeon": r"Xeon\s+(\w+)[-\s]*(\d{4}\w*)",
        "epyc": r"EPYC\s+(\d{4}\w*)",
        "threadripper": r"Threadripper\s+(\w*)\s*(\d{4}\w*)",
    }
    
    def __init__(self):
        self.logger = logging.getLogger("cpu_matcher")
        self.manual_mappings: Dict[str, str] = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance"""
        self._mfg_patterns = [re.compile(p, re.IGNORECASE) for p in self.MANUFACTURER_PREFIXES]
        self._suffix_patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in self.SUFFIX_PATTERNS.items()]
        self._model_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.MODEL_PATTERNS.items()}
    
    def normalize(self, name: str) -> str:
        """
        Normalize CPU name for matching
        - Remove manufacturer prefix
        - Standardize spacing
        - Remove common suffixes
        - Lowercase
        """
        if not name:
            return ""
        
        result = name.strip()
        
        # Remove manufacturer prefixes
        for pattern in self._mfg_patterns:
            result = pattern.sub("", result)
        
        # Remove common suffixes
        for pattern, replacement in self._suffix_patterns:
            result = pattern.sub(replacement, result)
        
        # Normalize whitespace and case
        result = re.sub(r"\s+", " ", result).strip().lower()
        
        return result
    
    def extract_model_number(self, name: str) -> Optional[str]:
        """Extract the model number from CPU name"""
        name_lower = name.lower()
        
        for family, pattern in self._model_patterns.items():
            if family in name_lower:
                match = pattern.search(name)
                if match:
                    return "".join(g for g in match.groups() if g).lower()
        
        return None
    
    def similarity_ratio(self, name1: str, name2: str) -> float:
        """Calculate string similarity ratio (0.0 to 1.0)"""
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
    
    def token_match_score(self, name1: str, name2: str) -> float:
        """
        Calculate token-based match score
        Higher weight for matching model numbers
        """
        tokens1 = set(self.normalize(name1).split())
        tokens2 = set(self.normalize(name2).split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        common = tokens1 & tokens2
        total = tokens1 | tokens2
        
        # Basic Jaccard similarity
        score = len(common) / len(total)
        
        # Bonus for model number match
        model1 = self.extract_model_number(name1)
        model2 = self.extract_model_number(name2)
        
        if model1 and model2 and model1 == model2:
            score = min(1.0, score + 0.3)
        
        return score
    
    def match(self, source_name: str, candidates: List[str], threshold: float = 0.8) -> Optional[Tuple[str, float]]:
        """
        Find best match for source_name among candidates
        Returns (matched_name, confidence) or None if no good match
        """
        # Check manual mappings first
        if source_name in self.manual_mappings:
            return (self.manual_mappings[source_name], 1.0)
        
        normalized_source = self.normalize(source_name)
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            normalized_candidate = self.normalize(candidate)
            
            # Exact match after normalization
            if normalized_source == normalized_candidate:
                return (candidate, 1.0)
            
            # Calculate combined score
            string_sim = self.similarity_ratio(normalized_source, normalized_candidate)
            token_sim = self.token_match_score(source_name, candidate)
            
            # Weighted combination
            score = (string_sim * 0.6) + (token_sim * 0.4)
            
            # Bonus for model number match
            model_source = self.extract_model_number(source_name)
            model_candidate = self.extract_model_number(candidate)
            if model_source and model_candidate and model_source == model_candidate:
                score = min(1.0, score + 0.2)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_match and best_score >= threshold:
            return (best_match, best_score)
        
        return None
    
    def match_all(self, source_names: List[str], candidates: List[str], 
                  threshold: float = 0.8) -> Dict[str, Tuple[Optional[str], float]]:
        """
        Match multiple source names against candidates
        Returns dict mapping source_name -> (matched_name, confidence)
        """
        results = {}
        
        for source_name in source_names:
            match_result = self.match(source_name, candidates, threshold)
            if match_result:
                results[source_name] = match_result
            else:
                results[source_name] = (None, 0.0)
        
        return results
    
    def add_manual_mapping(self, source_name: str, canonical_name: str):
        """Add a manual override mapping"""
        self.manual_mappings[source_name] = canonical_name
    
    def get_manufacturer(self, name: str) -> Optional[str]:
        """Extract manufacturer from CPU name"""
        name_lower = name.lower()
        
        if any(x in name_lower for x in ["ryzen", "epyc", "athlon", "threadripper", "amd"]):
            return "AMD"
        elif any(x in name_lower for x in ["core", "xeon", "celeron", "pentium", "intel"]):
            return "Intel"
        
        return None


# Singleton instance for reuse
_matcher_instance: Optional[CpuMatcher] = None

def get_matcher() -> CpuMatcher:
    """Get singleton CpuMatcher instance"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = CpuMatcher()
    return _matcher_instance
