#!/usr/bin/env python3
"""
Main PDF generation orchestration for the Segment Schedule Report Generator.
"""

import os
import logging
from typing import Dict, List, Optional

import pandas as pd
from weasyprint import HTML

from data_loader import DataLoader
from checklist_generator import ChecklistGenerator
from schedule_generator import ScheduleGenerator
from html_formatter import HTMLFormatter
from utils import find_col_case_insensitive, find_user_row, sanitize_filename

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Main orchestrator for PDF generation."""
    
    def __init__(
        self,
        analysis_excel_path: str = "data/analysis/analisis de datos.xlsx",
        segmentos_excel_path: str = "templates/Segmentos.xlsx",
        html_template_path: str = "templates/plantilla_plan_de_estudio.html",
    ):
        self.data_loader = DataLoader(analysis_excel_path, segmentos_excel_path)
        self.checklist_generator = ChecklistGenerator(self.data_loader)
        self.schedule_generator = ScheduleGenerator(self.data_loader)
        self.html_formatter = HTMLFormatter(html_template_path)

    def generate_pdf_for_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        variant: str = "manana",  # "manana" or "tarde"
        test_type_filter: Optional[str] = None,  # "CIEN" or "HYST" for special segments
    ) -> bytes:
        """Generate PDF for a single user."""
        if not (user_id or email):
            raise ValueError("Must provide user_id or email")

        self.data_loader.ensure_analysis_loaded()
        self.data_loader.ensure_segmentos_loaded()

        # Fetch user row from Reporte
        reporte_row = find_user_row(self.data_loader.df_reporte, user_id, email)
        if reporte_row is None:
            raise ValueError("User not found in 'Reporte' sheet")

        # Get segment key and user display name
        col_segmento = find_col_case_insensitive(self.data_loader.df_reporte, ["Segmento"]) or "Segmento"
        col_nombre = find_col_case_insensitive(self.data_loader.df_reporte, ["nombre_y_apellido"]) or "nombre_y_apellido"
        segmento_value = str(reporte_row.get(col_segmento, "")).strip()
        alumno_nombre = str(reporte_row.get(col_nombre, "Alumno")).strip()

        if not segmento_value:
            raise ValueError("User has empty 'Segmento' value")

        seg_df = self.data_loader.segment_key_to_df.get(segmento_value.upper())
        if seg_df is None:
            raise ValueError(f"Segment sheet for '{segmento_value}' not found in Segmentos.xlsx")

        # Select which segment sheet columns to use for this user based on levels from Reporte
        col_map = self.schedule_generator.select_schedule_columns(reporte_row, variant, segmento_value, test_type_filter)

        # Build schedule HTML
        schedule_html = self.schedule_generator.build_week_tables_html(seg_df, col_map)

        # Load template and inject content
        html_content = self.html_formatter.load_html_template()
        html_content = html_content.replace("<<ALUMNO>>", alumno_nombre)
        
        # Populate results table placeholders
        html_content = self.html_formatter.populate_results_table_placeholders(html_content, reporte_row, is_cuarto_medio=False)
        
        # Check if user is "Egresado" and conditionally include Calendario General section
        html_content = self.html_formatter.populate_calendario_general_section(html_content, reporte_row)
        
        if schedule_html:
            html_content = html_content.replace("</body>", f"{schedule_html}\n</body>")
        
        # Add checklist tables for Egresado students
        html_content = self.checklist_generator.add_checklist_to_html(html_content, reporte_row, is_cuarto_medio=False)

        # Render PDF
        html_doc = HTML(string=html_content)
        pdf_content = html_doc.write_pdf()
        return pdf_content

    def generate_pdf_for_cuarto_medio_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bytes:
        """Generate PDF for a "Cuarto medio" student (no schedule, only results table)."""
        if not (user_id or email):
            raise ValueError("Must provide user_id or email")

        self.data_loader.ensure_analysis_loaded()

        # Fetch user row from Reporte
        reporte_row = find_user_row(self.data_loader.df_reporte, user_id, email)
        if reporte_row is None:
            raise ValueError("User not found in 'Reporte' sheet")

        # Get user display name
        col_nombre = find_col_case_insensitive(self.data_loader.df_reporte, ["nombre_y_apellido"]) or "nombre_y_apellido"
        alumno_nombre = str(reporte_row.get(col_nombre, "Alumno")).strip()

        # Load template and inject content
        html_content = self.html_formatter.load_html_template()
        html_content = html_content.replace("<<ALUMNO>>", alumno_nombre)
        
        # Populate results table placeholders
        html_content = self.html_formatter.populate_results_table_placeholders(html_content, reporte_row, is_cuarto_medio=True)
        
        # For Cuarto medio students, do NOT include Calendario General section
        # (it's already excluded by default in _populate_calendario_general_section)
        
        # Do NOT include schedule tables for Cuarto medio students
        
        # Add checklist tables for Cuarto medio students
        html_content = self.checklist_generator.add_checklist_to_html(html_content, reporte_row, is_cuarto_medio=True)
        
        # Render PDF
        html_doc = HTML(string=html_content)
        pdf_content = html_doc.write_pdf()
        return pdf_content

    def check_existing_pdfs(self, output_dir: str) -> set:
        """Check for existing PDFs in the output directory and return a set of user identifiers."""
        existing_users = set()
        
        if not os.path.exists(output_dir):
            return existing_users
            
        # Walk through all subdirectories in the output directory
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.pdf'):
                    # Extract user identifier from filename
                    # Filename format: {base}_{variant}.pdf or {base}_CIEN_{variant}.pdf, etc.
                    filename_without_ext = file[:-4]  # Remove .pdf extension
                    
                    # Split by underscore and take the first part as the base identifier
                    parts = filename_without_ext.split('_')
                    if parts:
                        base_identifier = parts[0]
                        existing_users.add(base_identifier)
        
        logger.info(f"Found {len(existing_users)} users with existing PDFs")
        return existing_users

    def generate_pdfs_for_cuarto_medio_students(
        self,
        output_dir: str = "reports/Cuarto medio",
        existing_users: set = None
    ) -> Dict[str, int]:
        """Generate PDFs for all students with "Cuarto medio" status."""
        self.data_loader.ensure_analysis_loaded()
        
        # Find the student type column
        col_tipo_estudiante = find_col_case_insensitive(
            self.data_loader.df_reporte, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        col_user_id = find_col_case_insensitive(self.data_loader.df_reporte, ["user_id"]) or "user_id"
        col_email = find_col_case_insensitive(self.data_loader.df_reporte, ["email"]) or "email"

        # Filter for "Cuarto medio" students only
        if col_tipo_estudiante not in self.data_loader.df_reporte.columns:
            logger.warning(f"Column '{col_tipo_estudiante}' not found. No PDFs will be generated.")
            return {}
            
        # Case-insensitive filtering for "Cuarto medio" and empty values
        eligible = self.data_loader.df_reporte[
            (self.data_loader.df_reporte[col_tipo_estudiante].astype(str).str.strip().str.lower() == "cuarto medio") |
            (self.data_loader.df_reporte[col_tipo_estudiante].isna()) |
            (self.data_loader.df_reporte[col_tipo_estudiante].astype(str).str.strip() == "")
        ]
        
        logger.info(f"Found {len(eligible)} students with 'Cuarto medio' status or empty value")
        
        if len(eligible) == 0:
            logger.warning("No students with 'Cuarto medio' status or empty value found")
            return {}
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        total_count = 0
        skipped_count = 0
        
        for _, r in eligible.iterrows():
            user_id = r.get(col_user_id)
            email = r.get(col_email)
            
            # Create base identifier for checking existing PDFs
            base = email if pd.notna(email) and email else (user_id if pd.notna(user_id) else "user")
            base = sanitize_filename(base)
            
            # Check if user already has PDFs
            if existing_users and base in existing_users:
                logger.info(f"Skipping user {user_id}/{email} - PDF already exists")
                skipped_count += 1
                continue
            
            try:
                pdf = self.generate_pdf_for_cuarto_medio_user(
                    user_id=user_id if pd.notna(user_id) else None,
                    email=email if pd.notna(email) else None,
                )
                
                out_path = os.path.join(output_dir, f"{base}.pdf")
                with open(out_path, "wb") as f:
                    f.write(pdf)
                logger.info(f"Saved: {out_path}")
                total_count += 1
                
            except Exception as e:
                logger.error(f"Failed to generate PDF for user_id={user_id}, email={email}: {e}")
                continue
        
        logger.info(f"Generated {total_count} PDFs for Cuarto medio students, skipped {skipped_count} existing PDFs")
        return {"Cuarto medio": total_count}

    def generate_pdfs_for_egresado_students(
        self,
        output_dir: str = "reports",
        variants: List[str] = None,
        existing_users: set = None,
        segments_filter: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Generate PDFs for all students with "Egresado" status."""
        # Segments that get both mañana and tarde variants
        dual_variant_segments = {"S1", "S2", "S4", "S5"}
        
        # Special segments S7, S8, S15 with specific PDF generation rules
        special_s7_s8_s15_segments = {"S7", "S8", "S15"}
        
        if variants is None:
            variants = ["manana", "tarde"]
            
        self.data_loader.ensure_analysis_loaded()
        
        # Find the student type column
        col_tipo_estudiante = find_col_case_insensitive(
            self.data_loader.df_reporte, 
            ["qué_tipo_de_estudiante_eres", "que_tipo_de_estudiante_eres"]
        ) or "qué_tipo_de_estudiante_eres"
        
        col_user_id = find_col_case_insensitive(self.data_loader.df_reporte, ["user_id"]) or "user_id"
        col_email = find_col_case_insensitive(self.data_loader.df_reporte, ["email"]) or "email"
        col_segmento = find_col_case_insensitive(self.data_loader.df_reporte, ["Segmento"]) or "Segmento"

        # Filter for "Egresado" students only
        if col_tipo_estudiante not in self.data_loader.df_reporte.columns:
            logger.warning(f"Column '{col_tipo_estudiante}' not found. No PDFs will be generated.")
            return {}
            
        # Case-insensitive filtering for "Egresado"
        eligible = self.data_loader.df_reporte[
            self.data_loader.df_reporte[col_tipo_estudiante].astype(str).str.strip().str.lower() == "egresado"
        ]
        
        logger.info(f"Found {len(eligible)} students with 'Egresado' status")
        
        if len(eligible) == 0:
            logger.warning("No students with 'Egresado' status found")
            return {}
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        segment_counts = {}
        total_count = 0
        
        for _, r in eligible.iterrows():
            user_id = r.get(col_user_id)
            email = r.get(col_email)
            segmento = r.get(col_segmento)
            
            # Skip if no segmento value
            if pd.isna(segmento) or not str(segmento).strip():
                logger.warning(f"Skipping user {user_id}/{email} - no segmento value")
                continue
                
            # Create segment folder
            segmento_str = str(segmento).strip().upper()
            
            # Skip if segment is not in the filter
            if segments_filter and segmento_str not in segments_filter:
                logger.info(f"Skipping user {user_id}/{email} - segment {segmento_str} not in filter {segments_filter}")
                continue
                
            segment_folder = os.path.join(output_dir, segmento_str)
            os.makedirs(segment_folder, exist_ok=True)
            
            # Initialize count for this segment
            if segmento_str not in segment_counts:
                segment_counts[segmento_str] = 0
            
            base = email if pd.notna(email) and email else (user_id if pd.notna(user_id) else "user")
            base = sanitize_filename(base)
            
            # Check if user already has PDFs
            if existing_users and base in existing_users:
                logger.info(f"Skipping user {user_id}/{email} - PDF already exists")
                continue

            # Determine which variants to generate based on segment
            if segmento_str == "S13":
                # S13: Generate 4 PDFs total - S1 behavior (M1+CIEN) + S2 behavior (M1+HYST)
                # 1. S1 behavior: M1 + CIEN (mañana variant)
                # 2. S1 behavior: M1 + CIEN (tarde variant)
                # 3. S2 behavior: M1 + HYST (mañana variant)  
                # 4. S2 behavior: M1 + HYST (tarde variant)
                
                # Generate S1 behavior PDFs (M1 + CIEN)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S1_BEHAVIOR",  # Custom flag for S1 behavior
                        )
                        out_path = os.path.join(segment_folder, f"{base}_CIEN_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S1 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                
                # Generate S2 behavior PDFs (M1 + HYST)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S2_BEHAVIOR",  # Custom flag for S2 behavior
                        )
                        out_path = os.path.join(segment_folder, f"{base}_HYST_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S2 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                        
            elif segmento_str == "S14":
                # S14: Generate 4 PDFs total - S4 behavior (CL+CIEN) + S5 behavior (CL+HYST)
                # 1. S4 behavior: CL + CIEN (mañana variant)
                # 2. S4 behavior: CL + CIEN (tarde variant)
                # 3. S5 behavior: CL + HYST (mañana variant)  
                # 4. S5 behavior: CL + HYST (tarde variant)
                
                # Generate S4 behavior PDFs (CL + CIEN)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S4_BEHAVIOR",  # This will show CL + CIEN (S4 behavior)
                        )
                        out_path = os.path.join(segment_folder, f"{base}_CIEN_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S4 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                
                # Generate S5 behavior PDFs (CL + HYST)
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                            test_type_filter="S5_BEHAVIOR",  # This will show CL + HYST (S5 behavior)
                        )
                        out_path = os.path.join(segment_folder, f"{base}_HYST_{variant}.pdf")
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate S5 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
                        
            elif segmento_str in special_s7_s8_s15_segments:
                # Special handling for S7, S8, S15 with conditional PDF generation
                if segmento_str == "S7":
                    # S7: Conditional PDFs (mañana/tarde with CIEN based on student levels)
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student
                            mapping = self.schedule_generator.select_schedule_columns(r, variant, segmento_str, "CIEN")
                            if mapping["CIEN"] is None:
                                logger.info(f"Skipping S7 {variant} variant for user {user_id}/{email} - no valid CIEN mapping")
                                continue
                                
                            pdf = self.generate_pdf_for_user(
                                user_id=user_id if pd.notna(user_id) else None,
                                email=email if pd.notna(email) else None,
                                variant=variant,
                                test_type_filter="CIEN",
                            )
                            out_path = os.path.join(segment_folder, f"{base}_{variant}.pdf")
                            with open(out_path, "wb") as f:
                                f.write(pdf)
                            logger.info(f"Saved: {out_path}")
                            segment_counts[segmento_str] += 1
                            total_count += 1
                        except Exception as e:
                            logger.error(f"Failed to generate S7 CIEN schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                            
                elif segmento_str == "S8":
                    # S8: Conditional PDFs (mañana/tarde with HYST based on student levels)
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student
                            mapping = self.schedule_generator.select_schedule_columns(r, variant, segmento_str, "HYST")
                            if mapping["HYST"] is None:
                                logger.info(f"Skipping S8 {variant} variant for user {user_id}/{email} - no valid HYST mapping")
                                continue
                                
                            pdf = self.generate_pdf_for_user(
                                user_id=user_id if pd.notna(user_id) else None,
                                email=email if pd.notna(email) else None,
                                variant=variant,
                                test_type_filter="HYST",
                            )
                            out_path = os.path.join(segment_folder, f"{base}_{variant}.pdf")
                            with open(out_path, "wb") as f:
                                f.write(pdf)
                            logger.info(f"Saved: {out_path}")
                            segment_counts[segmento_str] += 1
                            total_count += 1
                        except Exception as e:
                            logger.error(f"Failed to generate S8 HYST schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                            
                elif segmento_str == "S15":
                    # S15: Generate maximum 4 PDFs - S7 behavior (M1+CL+CIEN) + S8 behavior (M1+CL+HYST)
                    # Uses conditional logic from S7 and S8 to determine which variants are available
                    
                    # Generate S7 behavior PDFs (M1 + CL + CIEN) - conditional based on student levels
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student using S7 logic
                            mapping = self.schedule_generator.select_schedule_columns(r, variant, "S7", "CIEN")
                            if mapping["CIEN"] is not None:
                                pdf = self.generate_pdf_for_user(
                                    user_id=user_id if pd.notna(user_id) else None,
                                    email=email if pd.notna(email) else None,
                                    variant=variant,
                                    test_type_filter="S7_BEHAVIOR",  # Custom flag for S7 behavior
                                )
                                out_path = os.path.join(segment_folder, f"{base}_S7_{variant}.pdf")
                                with open(out_path, "wb") as f:
                                    f.write(pdf)
                                logger.info(f"Saved: {out_path}")
                                segment_counts[segmento_str] += 1
                                total_count += 1
                            else:
                                logger.info(f"Skipping S15 S7 {variant} variant for user {user_id}/{email} - no valid CIEN mapping")
                        except Exception as e:
                            logger.error(f"Failed to generate S7 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                    
                    # Generate S8 behavior PDFs (M1 + CL + HYST) - conditional based on student levels
                    for variant in variants:
                        try:
                            # Check if this variant should be generated for this student using S8 logic
                            mapping = self.schedule_generator.select_schedule_columns(r, variant, "S8", "HYST")
                            if mapping["HYST"] is not None:
                                pdf = self.generate_pdf_for_user(
                                    user_id=user_id if pd.notna(user_id) else None,
                                    email=email if pd.notna(email) else None,
                                    variant=variant,
                                    test_type_filter="S8_BEHAVIOR",  # Custom flag for S8 behavior
                                )
                                out_path = os.path.join(segment_folder, f"{base}_S8_{variant}.pdf")
                                with open(out_path, "wb") as f:
                                    f.write(pdf)
                                logger.info(f"Saved: {out_path}")
                                segment_counts[segmento_str] += 1
                                total_count += 1
                            else:
                                logger.info(f"Skipping S15 S8 {variant} variant for user {user_id}/{email} - no valid HYST mapping")
                        except Exception as e:
                            logger.error(f"Failed to generate S8 behavior for user_id={user_id}, email={email}, variant={variant}: {e}")
                            continue
                        
            elif segmento_str in dual_variant_segments:
                # Generate both mañana and tarde variants
                for variant in variants:
                    try:
                        pdf = self.generate_pdf_for_user(
                            user_id=user_id if pd.notna(user_id) else None,
                            email=email if pd.notna(email) else None,
                            variant=variant,
                        )
                        
                        # For dual variant segments, include the variant in filename
                        out_path = os.path.join(segment_folder, f"{base}_segmento_{variant}.pdf")
                        
                        with open(out_path, "wb") as f:
                            f.write(pdf)
                        logger.info(f"Saved: {out_path}")
                        segment_counts[segmento_str] += 1
                        total_count += 1
                    except Exception as e:
                        logger.error(f"Failed to generate schedule for user_id={user_id}, email={email}, variant={variant}: {e}")
                        continue
            else:
                # Generate only one PDF (mañana variant)
                try:
                    pdf = self.generate_pdf_for_user(
                        user_id=user_id if pd.notna(user_id) else None,
                        email=email if pd.notna(email) else None,
                        variant="manana",
                    )
                    
                    # For single variant segments, don't include variant in filename
                    out_path = os.path.join(segment_folder, f"{base}.pdf")
                    
                    with open(out_path, "wb") as f:
                        f.write(pdf)
                    logger.info(f"Saved: {out_path}")
                    segment_counts[segmento_str] += 1
                    total_count += 1
                except Exception as e:
                    logger.error(f"Failed to generate schedule for user_id={user_id}, email={email}: {e}")
                    continue

        logger.info(f"Generated {total_count} schedule PDFs for Egresado students across {len(segment_counts)} segments")
        return segment_counts

    def generate_all_reports(
        self, 
        segments: Optional[List[str]] = None, 
        student_types: Optional[List[str]] = None
    ) -> bool:
        """Generate segment schedule reports for both "Egresado" and "Cuarto medio" students."""
        try:
            logger.info("Starting segment schedule report generation...")
            
            # Set defaults if not provided
            if segments is None:
                segments = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14", "S15"]
            if student_types is None:
                student_types = ["Egresado", "Cuarto medio"]
            
            logger.info(f"Generating PDFs for segments: {segments}")
            logger.info(f"Generating PDFs for student types: {student_types}")
            
            # Check for existing PDFs in both output directories
            logger.info("Checking for existing PDFs...")
            existing_egresado_pdfs = self.check_existing_pdfs("reports")
            existing_cuarto_medio_pdfs = self.check_existing_pdfs("reports/Cuarto medio")
            
            # Combine all existing users to avoid duplicates
            all_existing_users = existing_egresado_pdfs.union(existing_cuarto_medio_pdfs)
            logger.info(f"Found {len(all_existing_users)} total users with existing PDFs")
            
            egresado_results = {}
            cuarto_medio_results = {}
            
            # Generate PDFs for Egresado students
            if "Egresado" in student_types:
                logger.info("Generating PDFs for Egresado students...")
                egresado_results = self.generate_pdfs_for_egresado_students(
                    output_dir="reports",
                    variants=["manana", "tarde"],
                    existing_users=all_existing_users,
                    segments_filter=segments
                )
            
            # Generate PDFs for Cuarto medio students
            if "Cuarto medio" in student_types:
                logger.info("Generating PDFs for Cuarto medio students...")
                cuarto_medio_results = self.generate_pdfs_for_cuarto_medio_students(
                    output_dir="reports/Cuarto medio",
                    existing_users=all_existing_users
                )
            
            # Log results
            logger.info("=== Report Generation Results ===")
            if egresado_results:
                logger.info("Egresado students:")
                for segment, count in egresado_results.items():
                    logger.info(f"  {segment}: {count} PDFs")
            
            if cuarto_medio_results:
                logger.info("Cuarto medio students:")
                for category, count in cuarto_medio_results.items():
                    logger.info(f"  {category}: {count} PDFs")
            
            total_egresado = sum(egresado_results.values())
            total_cuarto_medio = sum(cuarto_medio_results.values())
            logger.info(f"Total PDFs generated: {total_egresado + total_cuarto_medio}")
            logger.info("=== End Results ===")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating segment schedule reports: {e}")
            return False
