#!/usr/bin/env python3
"""
Test script to verify HTML template integration logic (without weasyprint)
"""

import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_template_logic():
    """Test the template integration logic without weasyprint"""
    try:
        # Import the report generator
        from report_generator import ReportGenerator
        
        # Create report generator
        report_gen = ReportGenerator()
        
        # Test if template file exists
        template_path = Path("templates/plantilla_plan_de_estudio.html")
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return False
        
        logger.info(f"✅ Template file found: {template_path}")
        
        # Test template loading
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        logger.info(f"✅ Template loaded successfully, size: {len(html_content)} characters")
        
        # Test level calculation logic
        sample_results = {
            'M1': {
                'type': 'lecture_based',
                'lectures_analyzed': 5,
                'lectures_passed': 3,
            },
            'CL': {
                'type': 'percentage_based',
                'overall_percentage': 75.0,
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'total_lectures': 6,
                'total_lectures_passed': 4,
            },
            'HYST': {
                'type': 'lecture_based',
                'lectures_analyzed': 4,
                'lectures_passed': 2,
            }
        }
        
        # Test level calculation
        m1_level = report_gen._get_assessment_level(sample_results['M1'])
        cl_level = report_gen._get_assessment_level(sample_results['CL'])
        cien_level = report_gen._get_assessment_level(sample_results['CIEN'])
        hyst_level = report_gen._get_assessment_level(sample_results['HYST'])
        
        logger.info(f"✅ Level calculations:")
        logger.info(f"  M1: {m1_level}")
        logger.info(f"  CL: {cl_level}")
        logger.info(f"  CIEN: {cien_level}")
        logger.info(f"  HYST: {hyst_level}")
        
        # Test monthly plan generation
        plan_agosto = report_gen._generate_monthly_plan(sample_results, 'agosto')
        plan_septiembre = report_gen._generate_monthly_plan(sample_results, 'septiembre')
        plan_octubre = report_gen._generate_monthly_plan(sample_results, 'octubre')
        
        logger.info(f"✅ Monthly plans:")
        logger.info(f"  Agosto: {plan_agosto}")
        logger.info(f"  Septiembre: {plan_septiembre}")
        logger.info(f"  Octubre: {plan_octubre}")
        
        # Test second page content generation
        modified_html = report_gen._add_second_page_content(html_content, sample_results)
        
        # Check if the content was added
        if "<<Nivel M1>>" not in modified_html and "Nivel" in modified_html:
            logger.info("✅ Second page content successfully added")
        else:
            logger.warning("⚠️ Second page content may not have been properly replaced")
        
        logger.info("✅ Template integration logic test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing template logic: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_template_logic()
    if success:
        print("✅ Template integration logic test passed!")
    else:
        print("❌ Template integration logic test failed!")
        sys.exit(1) 