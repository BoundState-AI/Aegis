"""
Acronym discovery script - analyzes documents to find likely acronyms
and generates acronyms.json configuration file.
"""

import re
import json
import logging
from pathlib import Path
from collections import Counter
from typing import Set, Dict, List, Tuple

# Added imports for file handling
import docx
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class AcronymDiscoverer:
    """Discover acronyms from document corpus."""
    
    def __init__(self):
        # Pattern to find potential acronyms
        self.acronym_pattern = re.compile(r'\b[A-Z]{2,10}(?:\d{0,3})?\b')
        
        # Document ID pattern to exclude
        self.doc_id_pattern = re.compile(r'\b[GPWTF]\d{4}(?:\.\d+[A-Z]?)?(?:\s*r\d+)?\b', re.I)
        
        # Common words to exclude (minimal set)
        self.common_words = {
            'THE', 'AND', 'FOR', 'WITH', 'ARE', 'NOT', 'THIS', 'THAT',
            'FROM', 'INTO', 'BEEN', 'HAVE', 'WILL', 'WOULD', 'COULD',
            'SHOULD', 'MAY', 'CAN', 'MUST', 'SHALL'
        }
        
        # Patterns that indicate acronym definitions
        self.definition_patterns = [
            re.compile(r'([A-Z]{2,10})\s*\([^)]+\)', re.I),  # NASA (National Aeronautics...)
            re.compile(r'\(([A-Z]{2,10})\)', re.I),  # (NASA)
            re.compile(r'(?:known as|called|abbreviated)\s+([A-Z]{2,10})', re.I),
        ]
    
    def analyze_file(self, file_path: Path) -> Dict[str, int]:
        """Analyze a single file for acronyms."""
        try:
            ext = file_path.suffix.lower()
            text = ''
            
            if ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.pdf':
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() + '\n'
            elif ext == '.docx':
                doc = docx.Document(file_path)
                text = '\n'.join(para.text for para in doc.paragraphs)
            elif ext == '.doc':
                logger.warning(f"Skipping .doc file: {file_path} (handling not implemented)")
                return {}
            else:
                logger.debug(f"Unsupported file type: {file_path}")
                return {}
            
            # Find all potential acronyms
            candidates = self.acronym_pattern.findall(text)
            
            # Filter out document IDs
            doc_ids = set(self.doc_id_pattern.findall(text.upper()))
            
            # Count occurrences
            acronym_counts = Counter()
            for candidate in candidates:
                if candidate not in doc_ids and candidate not in self.common_words:
                    acronym_counts[candidate] += 1
            
            # Look for defined acronyms (higher confidence)
            for pattern in self.definition_patterns:
                for match in pattern.finditer(text):
                    acronym = match.group(1).upper()
                    if acronym and len(acronym) >= 2:
                        acronym_counts[acronym] += 10  # Boost defined acronyms
            
            return dict(acronym_counts)
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {}
    
    def discover_acronyms(self, 
                         directory: Path, 
                         min_occurrences: int = 3,
                         min_files: int = 2) -> List[Tuple[str, int, int]]:
        """
        Discover acronyms from a directory of documents.
        
        Returns list of (acronym, total_count, file_count) tuples.
        """
        # Extensions to analyze
        extensions = ['.txt', '.md', '.pdf', '.docx', '.doc']
        
        # Track acronyms across all files
        global_counts = Counter()
        file_counts = Counter()
        
        # Find all relevant files
        files = []
        for ext in extensions:
            files.extend(directory.rglob(f'*{ext}'))
        
        logger.info(f"Analyzing {len(files)} files for acronyms...")
        
        # Analyze each file
        for file_path in files:
            file_acronyms = self.analyze_file(file_path)
            
            for acronym, count in file_acronyms.items():
                global_counts[acronym] += count
                file_counts[acronym] += 1
        
        # Filter by thresholds
        results = []
        for acronym in global_counts:
            total_count = global_counts[acronym]
            num_files = file_counts[acronym]
            
            # Apply filters
            if total_count >= min_occurrences and num_files >= min_files:
                results.append((acronym, total_count, num_files))
        
        # Sort by frequency
        results.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        return results
    
    def generate_config(self, 
                       discovered: List[Tuple[str, int, int]],
                       output_path: Path = Path("config/acronyms.json"),
                       confidence_threshold: float = 0.8) -> None:
        """Generate acronyms.json configuration file."""
        
        # Categorize by confidence
        high_confidence = []  # Appears in many files
        medium_confidence = []  # Appears frequently but in fewer files
        review_needed = []  # Might be false positives
        
        for acronym, total_count, file_count in discovered:
            # High confidence: many files or very frequent
            if file_count >= 5 or total_count >= 50:
                high_confidence.append(acronym)
            # Medium confidence: moderate presence
            elif file_count >= 3 or total_count >= 20:
                medium_confidence.append(acronym)
            # Needs review: less certain
            else:
                review_needed.append(acronym)
        
        # Build config structure
        config = {
            "acronyms": sorted(high_confidence + medium_confidence),
            "metadata": {
                "generated_by": "acronym_discovery.py",
                "high_confidence": sorted(high_confidence),
                "medium_confidence": sorted(medium_confidence),
                "review_needed": sorted(review_needed),
                "stats": {
                    "total_discovered": len(discovered),
                    "high_confidence_count": len(high_confidence),
                    "medium_confidence_count": len(medium_confidence),
                    "review_needed_count": len(review_needed)
                }
            }
        }
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write config file
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Generated acronym config at {output_path}")
        logger.info(f"Found {len(high_confidence)} high-confidence acronyms")
        logger.info(f"Found {len(medium_confidence)} medium-confidence acronyms")
        logger.info(f"Found {len(review_needed)} that need review")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover acronyms in document corpus")
    parser.add_argument("directory", type=Path, nargs='?', default=Path("../test_documents"),
                        help="Directory to analyze (default: ../test_documents)")
    parser.add_argument("--min-occurrences", type=int, default=3,
                        help="Minimum total occurrences (default: 3)")
    parser.add_argument("--min-files", type=int, default=2,
                        help="Minimum number of files (default: 2)")
    parser.add_argument("--output", type=Path, default=Path("config/acronyms.json"),
                        help="Output config file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run discovery
    discoverer = AcronymDiscoverer()
    
    logger.info(f"Starting acronym discovery in {args.directory}")
    discovered = discoverer.discover_acronyms(
        args.directory,
        min_occurrences=args.min_occurrences,
        min_files=args.min_files
    )
    
    # Show top discoveries
    logger.info("\nTop 20 discovered acronyms:")
    for acronym, count, files in discovered[:20]:
        logger.info(f"  {acronym:10s} - {count:4d} occurrences in {files:3d} files")
    
    # Generate config
    discoverer.generate_config(discovered, args.output)
    
    # Print review suggestions
    if discovered:
        print("\n" + "="*60)
        print("REVIEW SUGGESTIONS:")
        print("="*60)
        print("\nPotential false positives to check:")
        for acronym, count, files in discovered:
            # Flag suspicious ones
            if len(acronym) == 2 and count < 10:
                print(f"  - {acronym} (only {count} occurrences)")
            elif acronym.startswith('REV') or acronym.startswith('VER'):
                print(f"  - {acronym} (might be version marker)")
            elif re.match(r'^[A-Z]+\d+$', acronym):
                print(f"  - {acronym} (might be identifier, not acronym)")
    
    print(f"\nConfig saved to {args.output}")
    print("Review the 'review_needed' section and move valid acronyms to main list")


if __name__ == "__main__":
    main()