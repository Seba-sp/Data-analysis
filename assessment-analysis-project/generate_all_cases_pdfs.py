#!/usr/bin/env python3
"""
Script to generate PDFs for all M1 and CL level combinations
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

def create_all_test_cases():
    """Create test data for all M1 and CL level combinations"""
    test_cases = {
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 0.0
                    }
                },
                'total_lectures_passed': 0,
                'total_lectures': 1,
                'overall_percentage': 0.0,
                'status': 'Reprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 1,
                'overall_percentage': 33.3,
                'status': 'Reprobado'
            }
        },
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 50.0
                    }
                },
                'total_lectures_passed': 1,
                'total_lectures': 2,
                'overall_percentage': 50.0,
                'status': 'Aprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 1,
                'lectures_analyzed': 2,
                'overall_percentage': 50.0,
                'status': 'Aprobado'
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 0.0
                    }
                },
                'total_lectures_passed': 0,
                'total_lectures': 1,
                'overall_percentage': 0.0,
                'status': 'Reprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 1,
                'overall_percentage': 33.3,
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 50.0
                    }
                },
                'total_lectures_passed': 1,
                'total_lectures': 2,
                'overall_percentage': 50.0,
                'status': 'Aprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 1,
                'lectures_analyzed': 2,
                'overall_percentage': 50.0,
                'status': 'Aprobado'
            }
        },
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                        },
                        'percentage': 100.0
                    }
                },
                'total_lectures_passed': 2,
                'total_lectures': 2,
                'overall_percentage': 100.0,
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                        },
                        'percentage': 100.0
                    }
                },
                'total_lectures_passed': 2,
                'total_lectures': 2,
                'overall_percentage': 100.0,
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 0.0
                    }
                },
                'total_lectures_passed': 0,
                'total_lectures': 1,
                'overall_percentage': 0.0,
                'status': 'Reprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 0,
                'lectures_analyzed': 1,
                'overall_percentage': 33.3,
                'status': 'Reprobado'
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                        },
                        'percentage': 50.0
                    }
                },
                'total_lectures_passed': 1,
                'total_lectures': 2,
                'overall_percentage': 50.0,
                'status': 'Aprobado'
            },
            'HYST': {
                'type': 'lecture_based',
                'lecture_results': {
                    'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                    'Lección 2': {'status': 'Reprobado', 'questions_correct': 1, 'total_questions': 3}
                },
                'lectures_passed': 1,
                'lectures_analyzed': 2,
                'overall_percentage': 50.0,
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
            },
            'CIEN': {
                'type': 'lecture_based_with_materia',
                'materia_results': {
                    'Química': {
                        'lecture_results': {
                            'Lección 1': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2},
                            'Lección 2': {'status': 'Aprobado', 'questions_correct': 2, 'total_questions': 2}
                        },
                        'percentage': 100.0
                    }
                },
                'total_lectures_passed': 2,
                'total_lectures': 2,
                'overall_percentage': 100.0,
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
            }
        }
    }
    
    return test_cases

def generate_all_pdfs():
    """Generate PDFs for all test cases"""
    try:
        logger.info("Starting PDF generation for all test cases...")
        
        # Create sample folder
        sample_folder = Path("sample_pdfs")
        sample_folder.mkdir(exist_ok=True)
        logger.info(f"✅ Created sample folder: {sample_folder}")
        
        # Initialize report generator
        report_gen = ReportGenerator()
        logger.info("✅ Report generator initialized")
        
        # Get all test cases
        test_cases = create_all_test_cases()
        
        print("\n" + "="*80)
        print("GENERATING PDFs FOR ALL M1/CL LEVEL COMBINATIONS")
        print("="*80)
        
        generated_files = []
        
        for case_name, user_results in test_cases.items():
            print(f"\n📋 Generating PDF for: {case_name}")
            print("-" * 50)
            
            # Get M1 and CL levels for display
            m1_level = report_gen._get_assessment_level(user_results.get('M1', {}))
            cl_level = report_gen._get_assessment_level(user_results.get('CL', {}))
            
            print(f"   M1 Level: {m1_level}")
            print(f"   CL Level: {cl_level}")
            
            # Generate PDF
            output_filename = f"{case_name}.pdf"
            output_path = sample_folder / output_filename
            
            try:
                pdf_content = report_gen.generate_comprehensive_report(
                    user_id="test_user",
                    user_email="test@example.com",
                    username="Estudiante de Prueba",
                    user_results=user_results
                )
                
                # Save PDF to file
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
                
                file_size = os.path.getsize(output_path)
                print(f"   ✅ PDF generated: {output_filename} ({file_size:,} bytes)")
                generated_files.append(output_filename)
                
            except Exception as e:
                print(f"   ❌ Error generating PDF for {case_name}: {e}")
        
        print("\n" + "="*80)
        print("PDF GENERATION SUMMARY")
        print("="*80)
        print(f"📁 Sample folder: {sample_folder}")
        print(f"📄 Total PDFs generated: {len(generated_files)}")
        print(f"✅ Successfully generated: {len(generated_files)} PDFs")
        
        if generated_files:
            print(f"\n📋 Generated PDFs:")
            for filename in generated_files:
                print(f"   • {filename}")
        
        print(f"\n🎉 All PDFs have been generated in the '{sample_folder}' folder!")
        print(f"   You can now open each PDF to see how different M1/CL combinations look.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during PDF generation: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting PDF generation for all test cases...")
    
    success = generate_all_pdfs()
    
    if success:
        logger.info("🎉 All PDFs generated successfully!")
    else:
        logger.error("💥 PDF generation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 