#!/usr/bin/env python3
"""
Test script to verify HTML template integration with report generator
"""

import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from report_generator import ReportGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_template_integration():
    """Test the HTML template integration"""
    try:
        # Create report generator
        report_gen = ReportGenerator()
        
        # Create sample user results
        sample_results = {
            'M1': {
                'type': 'lecture_based',
                'lectures_analyzed': 5,
                'lectures_passed': 3,
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado'},
                    'Lección 2': {'status': 'Reprobado'},
                    'Lección 3': {'status': 'Aprobado'},
                    'Lección 4': {'status': 'Aprobado'},
                    'Lección 5': {'status': 'Reprobado'}
                }
            },
            'CL': {
                'type': 'percentage_based',
                'overall_percentage': 75.0,
                'lecture_results': {
                    'Lección 1': {'percentage': 80.0},
                    'Lección 2': {'percentage': 70.0}
                }
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'total_lectures': 6,
                'total_lectures_passed': 4,
                'materia_results': {
                    'Matemáticas': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado'},
                            'Lección 2': {'status': 'Aprobado'}
                        }
                    },
                    'Física': {
                        'lecture_results': {
                            'Lección 3': {'status': 'Reprobado'},
                            'Lección 4': {'status': 'Aprobado'}
                        }
                    }
                }
            },
            'HYST': {
                'type': 'lecture_based',
                'lectures_analyzed': 4,
                'lectures_passed': 2,
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado'},
                    'Lección 2': {'status': 'Reprobado'},
                    'Lección 3': {'status': 'Aprobado'},
                    'Lección 4': {'status': 'Reprobado'}
                }
            }
        }
        
        # Test PDF generation
        logger.info("Testing PDF generation with new template...")
        pdf_content = report_gen.generate_comprehensive_report(
            user_id="test_user_123",
            user_email="test@example.com",
            username="Juan Pérez",
            user_results=sample_results
        )
        
        # Save PDF for inspection
        output_path = Path("test_report.pdf")
        with open(output_path, "wb") as f:
            f.write(pdf_content)
        
        logger.info(f"✅ PDF generated successfully: {output_path}")
        logger.info(f"PDF size: {len(pdf_content)} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing template integration: {e}")
        return False

if __name__ == "__main__":
    success = test_template_integration()
    if success:
        print("✅ Template integration test passed!")
    else:
        print("❌ Template integration test failed!")
        sys.exit(1) 