#!/usr/bin/env python3
"""
Test script to generate a PDF with sample data using the existing HTML template
"""
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from report_generator import ReportGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_data():
    """Create sample assessment data for testing"""
    sample_user_results = {
        'M1': {
            'type': 'lecture_based',
            'lecture_results': {
                'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 4': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 5': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 6': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 7': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 8': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 9': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 10': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 11': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 12': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 13': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 14': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 15': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 16': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 17': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 18': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 19': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 20': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 21': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 22': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 23': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 24': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 25': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 26': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 27': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 28': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 29': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 30': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 31': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 32': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 33': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                'Lección 34': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                'Lección 35': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 36': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                'Lección 37': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3}
            },
            'lectures_passed': 15,
            'lectures_analyzed': 20,
            'overall_percentage': 75.0,
            'status': 'Aprobado'
        },
        'CL': {
            'type': 'percentage_based',
            'lecture_results': {
                'Lección 1': {'percentage': 75.0, 'questions_correct': 3, 'total_questions': 4},
                'Lección 2': {'percentage': 100.0, 'questions_correct': 2, 'total_questions': 2}
            },
            'overall_percentage': 87.5,
            'status': 'Aprobado'
        },
        'CIEN': {
            'type': 'lecture_based_with_materia',
            'materia_results': {
                'Química': {
                    'lecture_results': {
                        'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 3': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 4': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 5': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 6': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 7': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 8': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 9': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 10': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 11': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 12': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 13': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 14': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 15': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 16': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 17': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 18': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 19': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 20': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                    },
                    'percentage': 70.0
                },
                'Biología': {
                    'lecture_results': {
                        'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 3': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 4': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 5': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 6': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 7': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 8': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 9': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 10': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                    },
                    'percentage': 70.0
                },
                'Física': {
                    'lecture_results': {
                        'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 3': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 4': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 5': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 6': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 7': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 8': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 9': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 10': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                    },
                    'percentage': 80.0
                },
                'Matemáticas': {
                    'lecture_results': {
                        'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 3': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 4': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 5': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 4},
                        'Lección 6': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 7': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                        'Lección 8': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                        'Lección 9': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                        'Lección 10': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                    },
                    'percentage': 70.0
                }
            },
            'total_lectures_passed': 52,
            'total_lectures': 70,
            'overall_percentage': 74.3,
            'status': 'Aprobado'
        },
        'HYST': {
            'type': 'lecture_based',
            'lecture_results': {
                'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3}
            },
            'lectures_passed': 2,
            'lectures_analyzed': 2,
            'overall_percentage': 100.0,
            'status': 'Aprobado'
        },
    }
    
    return sample_user_results

def test_pdf_generation():
    """Test PDF generation with sample data"""
    try:
        logger.info("Starting PDF generation test...")
        
        # Create sample data
        sample_data = create_sample_data()
        logger.info("✅ Sample data created successfully")
        
        # Initialize report generator
        report_gen = ReportGenerator()
        logger.info("✅ Report generator initialized")
        
        # Generate PDF
        output_path = "test_sample_pdf_multi_page_complete.pdf"
        logger.info(f"Generating PDF: {output_path}")
        
        # Use the correct method name
        pdf_content = report_gen.generate_comprehensive_report(
            user_id="12345",
            user_email="test@example.com",
            username="Juan Pérez",
            user_results=sample_data
        )
        
        # Save PDF to file
        with open(output_path, 'wb') as f:
            f.write(pdf_content)
        
        success = True
        
        if success:
            logger.info(f"✅ PDF generated successfully: {output_path}")
            
            # Check if file exists and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"✅ PDF file created with size: {file_size} bytes")
                
                if file_size > 0:
                    logger.info("🎉 PDF generation test completed successfully!")
                    return True
                else:
                    logger.error("❌ PDF file is empty")
                    return False
            else:
                logger.error("❌ PDF file was not created")
                return False
        else:
            logger.error("❌ PDF generation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during PDF generation: {e}")
        return False

def check_weasyprint_installation():
    """Check if weasyprint is properly installed"""
    try:
        import weasyprint
        logger.info("✅ WeasyPrint is installed")
        
        # Try to get version
        try:
            version = weasyprint.__version__
            logger.info(f"✅ WeasyPrint version: {version}")
        except AttributeError:
            logger.info("✅ WeasyPrint installed (version unknown)")
            
        return True
    except ImportError as e:
        logger.error(f"❌ WeasyPrint not installed: {e}")
        logger.error("Please install weasyprint: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking WeasyPrint: {e}")
        return False

def check_template_file():
    """Check if the HTML template exists"""
    template_path = Path("templates/plantilla_plan_de_estudio.html")
    if template_path.exists():
        logger.info(f"✅ HTML template found: {template_path}")
        file_size = template_path.stat().st_size
        logger.info(f"✅ Template file size: {file_size} bytes")
        return True
    else:
        logger.error(f"❌ HTML template not found: {template_path}")
        return False

def main():
    """Main test function"""
    logger.info("Starting PDF generation test with sample data...")
    
    # Check prerequisites
    logger.info("Checking prerequisites...")
    
    if not check_weasyprint_installation():
        logger.error("💥 WeasyPrint installation check failed")
        sys.exit(1)
        
    if not check_template_file():
        logger.error("💥 Template file check failed")
        sys.exit(1)
    
    # Run PDF generation test
    success = test_pdf_generation()
    
    if success:
        logger.info("🎉 All tests passed! PDF generated successfully.")
        logger.info("📄 Check 'test_sample_pdf.pdf' for the generated file.")
    else:
        logger.error("💥 PDF generation test failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 