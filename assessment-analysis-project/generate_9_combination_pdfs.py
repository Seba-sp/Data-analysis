#!/usr/bin/env python3
"""
Generate PDFs for all 9 combinations of M1 and CL levels
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from report_generator import ReportGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test data with all 9 M1 and CL level combinations"""
    test_cases = {
        # M1: Nivel 1 combinations
        "M1_Nivel1_CL_Nivel1": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 2,
                'overall_percentage': 33.3,
                'status': 'Reprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 50.0, 'questions_correct': 2, 'total_questions': 4}
                },
                'overall_percentage': 50.0,
                'status': 'Reprobado'
            }
        },
        "M1_Nivel1_CL_Nivel2": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 2,
                'overall_percentage': 33.3,
                'status': 'Reprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 70.0, 'questions_correct': 3, 'total_questions': 4},
                    'Lección 2': {'percentage': 60.0, 'questions_correct': 1, 'total_questions': 2}
                },
                'overall_percentage': 65.0,
                'status': 'Aprobado'
            }
        },
        "M1_Nivel1_CL_Nivel3": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 2,
                'overall_percentage': 33.3,
                'status': 'Reprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 100.0, 'questions_correct': 4, 'total_questions': 4},
                    'Lección 2': {'percentage': 100.0, 'questions_correct': 2, 'total_questions': 2}
                },
                'overall_percentage': 100.0,
                'status': 'Aprobado'
            }
        },
        
        # M1: Nivel 2 combinations
        "M1_Nivel2_CL_Nivel1": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 2,
                'lectures_analyzed': 3,
                'overall_percentage': 66.7,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 50.0, 'questions_correct': 2, 'total_questions': 4}
                },
                'overall_percentage': 50.0,
                'status': 'Reprobado'
            }
        },
        "M1_Nivel2_CL_Nivel2": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 2,
                'lectures_analyzed': 3,
                'overall_percentage': 66.7,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 70.0, 'questions_correct': 3, 'total_questions': 4},
                    'Lección 2': {'percentage': 60.0, 'questions_correct': 1, 'total_questions': 2}
                },
                'overall_percentage': 65.0,
                'status': 'Aprobado'
            }
        },
        "M1_Nivel2_CL_Nivel3": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 2,
                'lectures_analyzed': 3,
                'overall_percentage': 66.7,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 100.0, 'questions_correct': 4, 'total_questions': 4},
                    'Lección 2': {'percentage': 100.0, 'questions_correct': 2, 'total_questions': 2}
                },
                'overall_percentage': 100.0,
                'status': 'Aprobado'
            }
        },
        
        # M1: Nivel 3 combinations
        "M1_Nivel3_CL_Nivel1": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 3,
                'lectures_analyzed': 3,
                'overall_percentage': 88.9,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 50.0, 'questions_correct': 2, 'total_questions': 4}
                },
                'overall_percentage': 50.0,
                'status': 'Reprobado'
            }
        },
        "M1_Nivel3_CL_Nivel2": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 3,
                'lectures_analyzed': 3,
                'overall_percentage': 88.9,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 70.0, 'questions_correct': 3, 'total_questions': 4},
                    'Lección 2': {'percentage': 60.0, 'questions_correct': 1, 'total_questions': 2}
                },
                'overall_percentage': 65.0,
                'status': 'Aprobado'
            }
        },
        "M1_Nivel3_CL_Nivel3": {
            'M1': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 2': {'status': 'Aprobado', 'questions_correct': 3, 'total_questions': 3},
                    'Lección 3': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                },
                'lectures_passed': 3,
                'lectures_analyzed': 3,
                'overall_percentage': 88.9,
                'status': 'Aprobado'
            },
            'CL': {
                'type': 'percentage_based',
                'lecture_results': {
                    'Lección 1': {'percentage': 100.0, 'questions_correct': 4, 'total_questions': 4},
                    'Lección 2': {'percentage': 100.0, 'questions_correct': 2, 'total_questions': 2}
                },
                'overall_percentage': 100.0,
                'status': 'Aprobado'
            }
        }
    }
    
    return test_cases

def generate_combination_pdfs():
    """Generate PDFs for all 9 combinations"""
    try:
        logger.info("Starting PDF generation for all 9 M1/CL combinations...")
        
        # Initialize report generator
        report_gen = ReportGenerator()
        logger.info("✅ Report generator initialized")
        
        # Get test cases
        test_cases = create_test_data()
        
        # Create output directory
        output_dir = Path("combination_pdfs")
        output_dir.mkdir(exist_ok=True)
        
        print("\n" + "="*80)
        print("GENERATING PDFs FOR ALL 9 M1/CL COMBINATIONS")
        print("="*80)
        
        success_count = 0
        total_count = len(test_cases)
        
        for case_name, user_results in test_cases.items():
            print(f"\n📋 Generating PDF: {case_name}")
            print("-" * 50)
            
            # Get M1 and CL levels
            m1_level = report_gen._get_assessment_level(user_results.get('M1', {}))
            cl_level = report_gen._get_assessment_level(user_results.get('CL', {}))
            
            print(f"   M1 Level: {m1_level}")
            print(f"   CL Level: {cl_level}")
            
            # Test monthly plans
            months = ['agosto', 'septiembre', 'octubre']
            print(f"   Monthly Plans:")
            for month in months:
                plan = report_gen._generate_monthly_plan(user_results, month)
                print(f"     {month.capitalize()}: {plan}")
            
            # Generate PDF
            try:
                pdf_content = report_gen.generate_comprehensive_report(
                    user_id="test_user_123",
                    user_email="test@example.com",
                    username="Test Student",
                    user_results=user_results
                )
                
                # Save PDF
                output_filename = f"{case_name}.pdf"
                output_path = output_dir / output_filename
                
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
                
                file_size = len(pdf_content)
                print(f"   ✅ PDF generated: {output_filename} ({file_size:,} bytes)")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error generating PDF: {e}")
        
        print("\n" + "="*80)
        print(f"PDF GENERATION SUMMARY")
        print("="*80)
        print(f"✅ Successfully generated: {success_count}/{total_count} PDFs")
        print(f"📁 Output directory: {output_dir}")
        print(f"📄 PDFs saved with combination names")
        print("="*80)
        
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"❌ Error during PDF generation: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting 9 combination PDF generation...")
    
    success = generate_combination_pdfs()
    
    if success:
        logger.info("🎉 All 9 combination PDFs generated successfully!")
        print("\n🎉 All PDFs have been generated successfully!")
        print("📁 Check the 'combination_pdfs' folder for the generated files.")
    else:
        logger.error("💥 Some PDFs failed to generate.")
        sys.exit(1)

if __name__ == "__main__":
    main() 