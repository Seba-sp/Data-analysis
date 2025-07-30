#!/usr/bin/env python3
"""
Test script to verify the updated HTML template with new content and placeholders
"""

import logging
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_template_update():
    """Test the updated HTML template with new content"""
    try:
        # Read the template file
        template_path = Path("templates/plantilla_plan_de_estudio.html")
        
        if not template_path.exists():
            logger.error(f"Template file not found: {template_path}")
            return False
            
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        logger.info(f"✅ Template file loaded successfully, size: {len(template_content)} characters")
        
        # Check if the new content is present
        required_content = [
            "Te entrego tu plan de estudio personalizado",
            "¡VAMOS CON TODO!",
            "Estos son tus niveles asignados:",
            "En M1: <<Nivel M1>>",
            "En Competencia Lectora: <<Nivel CL>>",
            "En Ciencias: <<Nivel Ciencias>>",
            "En Historia y Cs. Sociales: <<Nivel Historia>>",
            "Según estos niveles, te sugiero el siguiente itinerario:",
            "Agosto: <<PlanAgosto>>",
            "Septiembre: <<PlanSeptiembre>>",
            "Octubre: <<PlanOctubre>>"
        ]
        
        missing_content = []
        for content in required_content:
            if content not in template_content:
                missing_content.append(content)
                
        if missing_content:
            logger.error(f"❌ Missing content in template: {missing_content}")
            return False
            
        logger.info("✅ All required content found in template")
        
        # Test placeholder replacement
        test_replacements = {
            '<<Nombre>>': 'Juan Pérez',
            '<<Nivel M1>>': 'Nivel 2',
            '<<Nivel CL>>': 'Nivel 3',
            '<<Nivel Ciencias>>': 'Nivel 1',
            '<<Nivel Historia>>': 'Nivel 2',
            '<<PlanAgosto>>': 'Enfoque en fundamentos básicos',
            '<<PlanSeptiembre>>': 'Desarrollo de habilidades intermedias',
            '<<PlanOctubre>>': 'Refinamiento de técnicas avanzadas'
        }
        
        test_content = template_content
        for placeholder, value in test_replacements.items():
            test_content = test_content.replace(placeholder, value)
            
        # Check if replacements worked
        if 'Juan Pérez' in test_content and 'Nivel 2' in test_content:
            logger.info("✅ Placeholder replacement test successful")
        else:
            logger.error("❌ Placeholder replacement test failed")
            return False
            
        logger.info("✅ Template update test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing template update: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting template update test...")
    
    success = test_template_update()
    
    if success:
        logger.info("🎉 All tests passed! Template is ready for use.")
    else:
        logger.error("💥 Some tests failed. Please check the template.")
        sys.exit(1)

if __name__ == "__main__":
    main() 