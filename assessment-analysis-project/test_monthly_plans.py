#!/usr/bin/env python3
"""
Test script to verify the new monthly plan logic
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
        "M1: Nivel 1, CL: Nivel 1": {
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
        "M1: Nivel 1, CL: Nivel 2": {
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
        "M1: Nivel 1, CL: Nivel 3": {
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
        "M1: Nivel 2, CL: Nivel 1": {
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
        "M1: Nivel 2, CL: Nivel 2": {
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
        "M1: Nivel 2, CL: Nivel 3": {
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
        "M1: Nivel 3, CL: Nivel 1": {
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
        "M1: Nivel 3, CL: Nivel 2": {
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
        "M1: Nivel 3, CL: Nivel 3": {
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

def test_monthly_plans():
    """Test the monthly plan generation logic"""
    try:
        logger.info("Testing monthly plan generation logic...")
        
        # Initialize report generator
        report_gen = ReportGenerator()
        logger.info("✅ Report generator initialized")
        
        # Get test cases
        test_cases = create_test_data()
        
        print("\n" + "="*60)
        print("MONTHLY PLAN LOGIC TEST RESULTS")
        print("="*60)
        
        for case_name, user_results in test_cases.items():
            print(f"\n📋 Test Case: {case_name}")
            print("-" * 40)
            
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
        
        print("\n" + "="*60)
        print("✅ Monthly plan logic test completed!")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during monthly plan test: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting monthly plan logic test...")
    
    success = test_monthly_plans()
    
    if success:
        logger.info("🎉 Monthly plan logic test completed successfully!")
    else:
        logger.error("💥 Monthly plan logic test failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 