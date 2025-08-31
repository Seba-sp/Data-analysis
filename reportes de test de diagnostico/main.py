#!/usr/bin/env python3
"""
Main entry point for the Segment Schedule Report Generator.
"""

import argparse
import logging
import sys
from typing import List, Optional

from pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('segment_schedule_generator.log')
        ]
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate segment schedule reports for students",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all reports for all segments and student types
  python main.py

  # Generate reports only for specific segments
  python main.py --segments S1 S2 S3

  # Generate reports only for Egresado students
  python main.py --student-types Egresado

  # Generate reports with debug logging
  python main.py --debug

  # Generate reports for specific segments with custom paths
  python main.py --segments S1 S2 --analysis-path "custom/path/analisis.xlsx"
        """
    )
    
    parser.add_argument(
        '--segments',
        nargs='+',
        help='Specific segments to generate reports for (e.g., S1 S2 S3). Default: all segments'
    )
    
    parser.add_argument(
        '--student-types',
        nargs='+',
        choices=['Egresado', 'Cuarto medio'],
        help='Student types to generate reports for. Default: both types'
    )
    
    parser.add_argument(
        '--analysis-path',
        default="data/analysis/analisis de datos.xlsx",
        help='Path to the analysis Excel file'
    )
    
    parser.add_argument(
        '--segmentos-path',
        default="templates/Segmentos.xlsx",
        help='Path to the segmentos Excel file'
    )
    
    parser.add_argument(
        '--template-path',
        default="templates/plantilla_plan_de_estudio.html",
        help='Path to the HTML template file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without actually creating files'
    )
    
    return parser.parse_args()


def main() -> int:
    """Main function."""
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.debug)
    
    logger.info("Starting Segment Schedule Report Generator")
    
    try:
        # Initialize the generator
        generator = PDFGenerator(
            analysis_excel_path=args.analysis_path,
            segmentos_excel_path=args.segmentos_path,
            html_template_path=args.template_path
        )
        
        # Set debug logging if requested
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        # Generate all reports
        success = generator.generate_all_reports(
            segments=args.segments,
            student_types=args.student_types
        )
        
        if success:
            logger.info("Report generation completed successfully")
            return 0
        else:
            logger.error("Report generation failed")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
