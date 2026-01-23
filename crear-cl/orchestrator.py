"""
Pipeline Orchestrator
Coordinates the 4-agent workflow for PAES question generation from news articles.

Workflow:
1. Agent 1: Text Curation (30 candidates, 28-column TSV with 10-10-10 distribution)
2. Agent 2: Legal Validation (license compliance, ~18-24 approved)  
3. Agent 3: Question Generation (10 PAES questions per article, 2-5-3 distribution)
4. Agent 4: Question Review (DEMRE standards, nota 0-10)
5. Agent 3: Question Improvement (apply feedback)
6. Document Generation & Upload (PDF + 2 DOCX files)
"""
import os
from typing import Optional, List, Dict
from datetime import datetime

from config import config
from storage import storage
from utils.state_manager import state_manager
from utils.document_generator import doc_generator
from utils.drive_manager import drive_manager
from agents.agent1_research import research_agent, ResearchAgent
from agents.agent2_validation import validation_agent
from agents.agent3_questions import question_agent, QuestionAgent
from agents.agent4_review import review_agent, ReviewAgent


class PipelineOrchestrator:
    """Orchestrates the multi-agent PAES question generation pipeline."""
    
    def __init__(self):
        """Initialize orchestrator with all components."""
        self.state_manager = state_manager
        self.doc_generator = doc_generator
        self.drive_manager = drive_manager
        self.research_agent = research_agent
        self.validation_agent = validation_agent
        self.question_agent = question_agent
        self.review_agent = review_agent
        self.output_dir = config.BASE_DATA_PATH  # Output directory for generated documents
        
        print("[Orchestrator] Initialized with all agents")
    
    def run_pipeline(self, 
                     num_batches: int = 1, 
                     topic: Optional[str] = None, 
                     count: int = 30,
                     agent1_mode: Optional[str] = None,
                     start_from: str = 'agent1',
                     tsv_file: Optional[str] = None,
                     candidatos_file: Optional[str] = None,
                     reverse: bool = False):
        """
        Run the complete PAES question generation pipeline.
        
        Args:
            num_batches: Number of batches to process
            topic: Research topic (None = "diversidad temática")
            count: Candidates per batch (default: 30 for PAES 10-10-10)
            agent1_mode: Override Agent 1 mode ('agent' or 'model')
            start_from: Starting point ('agent1', 'agent2', or 'agent3')
            tsv_file: TSV file for agent2/agent3 start
            candidatos_file: Optional candidatos TSV for agent3 start (backward compatibility)
            reverse: Process articles in reverse order (bottom to top)
        """
        # Override Agent 1 mode if specified
        if agent1_mode:
            self.research_agent = ResearchAgent(mode=agent1_mode)
            print(f"[Orchestrator] Using Agent 1 mode: {agent1_mode}")
        
        print(f"\n{'='*70}")
        print(f"[Orchestrator] PAES Question Generation Pipeline")
        print(f"{'='*70}")
        print(f"  Batches: {num_batches}")
        print(f"  Candidates per batch: {count}")
        print(f"  Starting from: {start_from}")
        if topic:
            print(f"  Topic: {topic}")
        if reverse:
            print(f"  Order: REVERSE (bottom to top)")
        print(f"{'='*70}\n")
        
        try:
            for batch_num in range(1, num_batches + 1):
                print(f"\n{'='*70}")
                print(f"[Orchestrator] BATCH {batch_num}/{num_batches}")
                print(f"[Orchestrator] Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}\n")
                
                try:
                    # Determine workflow based on start point
                    if start_from == 'agent3':
                        validated_articles = self._start_from_agent3(tsv_file, candidatos_file)
                    elif start_from == 'agent2':
                        validated_articles = self._start_from_agent2(tsv_file)
                    else:  # agent1
                        validated_articles = self._run_full_pipeline(topic, count)
                    
                    if not validated_articles:
                        print(f"[Orchestrator] No validated articles in batch {batch_num}")
                        continue
                    
                    # Reverse order if requested (for parallel processing)
                    if reverse:
                        validated_articles = list(reversed(validated_articles))
                        print(f"[Orchestrator] Processing in REVERSE order ({len(validated_articles)} articles)")
                    
                    # Process each validated article (Steps 3-6)
                    for i, article in enumerate(validated_articles, 1):
                        print(f"\n{'='*60}")
                        print(f"[Orchestrator] Article {i}/{len(validated_articles)}: {article.get('article_id', 'N/A')}")
                        print(f"{'='*60}")
                        self._process_article(article)
                    
                    # Upload master CSV
                    self._upload_master_csv()
                    
                    # Batch complete
                    processed_count = self.state_manager.get_processed_count()
                    print(f"\n{'='*70}")
                    print(f"[Orchestrator] Batch {batch_num}/{num_batches} COMPLETE")
                    print(f"[Orchestrator] Total processed: {processed_count} articles")
                    print(f"{'='*70}\n")
                
                except Exception as e:
                    print(f"\n[Orchestrator] ERROR in batch {batch_num}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        finally:
            # Restore original research agent
            if agent1_mode:
                self.research_agent = research_agent
        
        # Final statistics
        print(f"\n{'='*70}")
        print(f"[Orchestrator] ALL BATCHES COMPLETE ({num_batches} batches)")
        print(f"{'='*70}\n")
        self._print_statistics()
    
    def _run_full_pipeline(self, topic: Optional[str], count: int) -> List[Dict]:
        """Run complete pipeline: Agent 1 → Agent 2 → return validated articles."""
        # Get processed URLs for duplicate prevention
        processed_urls = self.state_manager.get_processed_urls()
        if processed_urls:
            print(f"[Orchestrator] Excluding {len(processed_urls)} already processed URLs")
        
        # Step 1: Research & Curation (Agent 1)
        articles = self._step1_research(topic, count, processed_urls)
        if not articles:
            return []
        
        # Step 2: Legal Validation (Agent 2)
        validated_articles = self._step2_validate(articles)
        return validated_articles
    
    def _start_from_agent2(self, tsv_file: Optional[str]) -> List[Dict]:
        """Start pipeline from Agent 2 (load candidatos TSV)."""
        print(f"[Orchestrator] Starting from Agent 2")
        
        # Find or use provided TSV file
        if not tsv_file:
            tsv_file = self._find_latest_file('candidatos_*.tsv')
            if not tsv_file:
                print(f"[Orchestrator] ERROR: No candidatos TSV found")
                return []
            print(f"[Orchestrator] Using: {os.path.basename(tsv_file)}")
        
        # Load TSV data
        with open(tsv_file, 'r', encoding='utf-8') as f:
            tsv_data = f.read()
        
        # Convert TSV to articles
        articles = self.research_agent.tsv_to_article_list(tsv_data)
        print(f"[Orchestrator] Loaded {len(articles)} candidates from TSV")
        
        # Add to state tracking
        article_ids = self.state_manager.add_articles(articles)
        for article, aid in zip(articles, article_ids):
            article['article_id'] = article.get('article_id', aid)
        
        # Validate with Agent 2
        self._last_tsv = tsv_data
        validated_articles = self._step2_validate(articles)
        return validated_articles
    
    def _start_from_agent3(self, tsv_file: Optional[str], 
                          candidatos_file: Optional[str] = None) -> List[Dict]:
        """
        Start pipeline from Agent 3 (load CSV with article data + DOCX paths).
        
        Args:
            tsv_file: Path to CSV file with Docx_Path column (or TSV for backward compatibility)
            candidatos_file: Ignored (backward compatibility)
        """
        import pandas as pd
        
        print(f"[Orchestrator] Starting from Agent 3")
        
        # Find or use provided file
        if not tsv_file:
            # Try CSV first, then TSV for backward compatibility
            csv_file = self._find_latest_file('*.csv')
            if csv_file:
                tsv_file = csv_file
            else:
                tsv_file = self._find_latest_file('auditoria_*.tsv')
            
            if not tsv_file:
                print(f"[Orchestrator] ERROR: No CSV or TSV found")
                return []
        
        file_ext = os.path.splitext(tsv_file)[1].lower()
        print(f"[Orchestrator] Input file: {os.path.basename(tsv_file)}")
        
        # Handle CSV files (new DOCX-based approach)
        if file_ext == '.csv':
            print(f"[Orchestrator] Loading CSV with DOCX paths")
            
            # Load CSV with pandas (support both comma and semicolon delimiters)
            try:
                df = pd.read_csv(tsv_file)
            except pd.errors.ParserError:
                # Try semicolon delimiter (common in European locales)
                df = pd.read_csv(tsv_file, sep=';')
            
            # Validate required columns
            required_cols = ['ID', 'Titulo', 'Docx_Path', 'Estado']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                print(f"[Orchestrator] ERROR: Missing columns: {missing}")
                return []
            
            # Filter for approved articles
            approved_df = df[df['Estado'].str.upper().isin(['APROBADO', 'APROBADO_CONDICION'])]
            print(f"[Orchestrator] Found {len(approved_df)} approved articles in CSV")
            
            # Convert to article dicts
            validated_articles = []
            for _, row in approved_df.iterrows():
                docx_path = row.get('Docx_Path', '')
                
                # Handle relative paths - make absolute
                if docx_path and not os.path.isabs(docx_path):
                    docx_path = os.path.abspath(docx_path)
                
                article = {
                    'article_id': row.get('ID', ''),
                    'title': row.get('Titulo', ''),
                    'author': row.get('Autor', ''),
                    'url': row.get('URL_Canonica', row.get('URL', '')),
                    'source': row.get('Fuente', ''),
                    'date': row.get('Ano', ''),
                    'type': row.get('Tipo', ''),
                    'license': row.get('Licencia', ''),
                    'docx_path': docx_path,  # Absolute path
                    'license_status': 'approved'
                }
                
                validated_articles.append(article)
            
            print(f"[Orchestrator] Loaded {len(validated_articles)} articles from CSV")
        
        # Handle TSV files (backward compatibility)
        else:
            print(f"[Orchestrator] Loading TSV (legacy mode)")
            
            # Load audit TSV
            with open(tsv_file, 'r', encoding='utf-8') as f:
                audit_tsv = f.read()
            
            # Load candidatos TSV if provided
            candidatos_tsv = None
            if candidatos_file:
                print(f"[Orchestrator] Candidatos TSV: {os.path.basename(candidatos_file)}")
                with open(candidatos_file, 'r', encoding='utf-8') as f:
                    candidatos_tsv = f.read()
            
            # Parse with Agent 2's method
            validated_articles = self.validation_agent._parse_audit_results(
                audit_tsv, candidatos_tsv
            )
            
            print(f"[Orchestrator] Loaded {len(validated_articles)} articles from TSV")
        
        # Add to state tracking
        for article in validated_articles:
            if article.get('article_id'):
                self.state_manager.update_license_validation(
                    article_id=article['article_id'],
                    license_status='approved',
                    license_type=article.get('license', 'CC'),
                    validation_reason='Pre-approved from input file'
                )
        
        return validated_articles
    
    def _step1_research(self, topic: Optional[str], count: int, 
                       exclude_urls: List[str]) -> List[Dict]:
        """Step 1: Text curation with Agent 1."""
        print(f"\n{'='*70}")
        print(f"[STEP 1] Text Curation - Agent 1")
        print(f"{'='*70}")
        
        # Get last ID for continuation
        last_id = self.state_manager.get_last_id()
        
        # Generate TSV with Agent 1
        tsv_data = self.research_agent.find_articles(
            topic=topic,
            count=count,
            exclude_urls=exclude_urls,
            last_id=last_id
        )
        
        if not tsv_data or len(tsv_data.strip().split('\n')) < 2:
            print("[STEP 1] ERROR: No candidates generated")
            return []
        
        # Save TSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        tsv_path = storage.save_text(tsv_data, f"candidatos_{timestamp}.tsv")
        print(f"[STEP 1] Saved TSV: {tsv_path}")
        
        # Store for Agent 2
        self._last_tsv = tsv_data
        
        # Convert to article list
        articles = self.research_agent.tsv_to_article_list(tsv_data)
        
        if not articles:
            print(f"[STEP 1] ERROR: Failed to parse TSV")
            return []
        
        # Add to state tracking
        article_ids = self.state_manager.add_articles(articles)
        for article, aid in zip(articles, article_ids):
            article['article_id'] = article.get('article_id', aid)
        
        print(f"[STEP 1] Complete: {len(articles)} candidates\n")
        return articles
    
    def _step2_validate(self, articles: List[Dict]) -> List[Dict]:
        """Step 2: Legal validation with Agent 2."""
        print(f"\n{'='*70}")
        print(f"[STEP 2] Legal Validation - Agent 2")
        print(f"{'='*70}")
        
        # Get TSV data
        tsv_data = getattr(self, '_last_tsv', '')
        if not tsv_data:
            print("[STEP 2] ERROR: No TSV data available")
            return []
        
        # Validate
        audit_tsv, approved_articles = self.validation_agent.validate_articles(tsv_data)
        
        if not audit_tsv:
            print("[STEP 2] WARNING: No audit results")
        else:
            # Save audit TSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audit_path = storage.save_text(audit_tsv, f"auditoria_{timestamp}.tsv")
            print(f"[STEP 2] Saved audit: {audit_path}")
            
            # Print summary
            summary = self.validation_agent.get_audit_summary(audit_tsv)
            print(f"[STEP 2] Results:")
            print(f"  Total: {summary['total']}")
            print(f"  APROBADO: {summary['aprobado']}")
            print(f"  RECHAZADO: {summary['rechazado']}")
        
        # Update state
        for article in articles:
            aid = article.get('article_id', article.get('url', ''))
            status = 'approved' if article in approved_articles else 'rejected'
            
            self.state_manager.update_license_validation(
                article_id=aid,
                license_status=status,
                license_type=article.get('license', 'unknown'),
                validation_reason='DEMRE legal audit'
            )
        
        print(f"[STEP 2] Complete: {len(approved_articles)}/{len(articles)} approved\n")
        return approved_articles
    
    def _process_article(self, article: Dict):
        """Process a single article through Steps 3-6."""
        article_id = article.get('article_id', 'unknown')
        title = article.get('title', 'Untitled')
        
        try:
            # Create fresh agent instances
            print(f"[Orchestrator] Creating fresh Agent 3 & 4 instances...")
            q_agent = QuestionAgent()
            r_agent = ReviewAgent()
            
            # Step 3: Generate questions
            print(f"\n[STEP 3] Question Generation - Agent 3")
            try:
                questions = q_agent.generate_questions(article)
            except FileNotFoundError as e:
                print(f"[STEP 3] Skipping {article_id}: {e}")
                self.state_manager.mark_error(article_id, f"DOCX file not found: {e}")
                return
            
            if not questions or not questions.get('questions'):
                print(f"[STEP 3] ERROR: No questions generated")
                self.state_manager.mark_error(article_id, "No questions generated")
                return
            
            self.state_manager.mark_questions_generated(article_id)
            
            # Step 4: Review questions
            print(f"\n[STEP 4] Question Review - Agent 4")
            try:
                feedback = r_agent.review_questions(article, questions)
            except Exception as e:
                print(f"[STEP 4] ERROR: {e}")
                import traceback
                traceback.print_exc()
                self.state_manager.mark_error(article_id, f"Review failed: {e}")
                return
            
            # Step 5: Improve questions
            print(f"\n[STEP 5] Question Improvement - Agent 3")
            try:
                improved = q_agent.improve_questions(questions, feedback, article)
            except Exception as e:
                print(f"[STEP 5] ERROR: {e}")
                import traceback
                traceback.print_exc()
                self.state_manager.mark_error(article_id, f"Improvement failed: {e}")
                return
            
            self.state_manager.mark_questions_improved(article_id)
            
            # Step 6: Generate documents
            print(f"\n[STEP 6] Document Generation")
            
            # Generate merged Word documents (article text + questions)
            try:
                questions_initial_word = self.doc_generator.merge_text_and_questions_docx(
                    source_docx_path=article.get('docx_path'),
                    questions=questions,
                    output_path=os.path.join(self.output_dir, f"questions_initial_{article_id}.docx"),
                    title=article.get('title', '')
                )
                print(f"[STEP 6] Initial Word: {os.path.basename(questions_initial_word)}")
            except Exception as e:
                print(f"[STEP 6] ERROR generating initial Word: {e}")
                questions_initial_word = None
            
            try:
                questions_improved_word = self.doc_generator.merge_text_and_questions_docx(
                    source_docx_path=article.get('docx_path'),
                    questions=improved,
                    output_path=os.path.join(self.output_dir, f"questions_improved_{article_id}.docx"),
                    title=article.get('title', '')
                )
                print(f"[STEP 6] Improved Word: {os.path.basename(questions_improved_word)}")
            except Exception as e:
                print(f"[STEP 6] ERROR generating improved Word: {e}")
                questions_improved_word = None
            
            # Generate Excel files (with answers, justifications, etc.)
            try:
                questions_initial_excel = self.doc_generator.generate_questions_excel(
                    questions, f"questions_initial_{article_id}.xlsx"
                )
                print(f"[STEP 6] Initial Excel: {os.path.basename(questions_initial_excel)}")
            except Exception as e:
                print(f"[STEP 6] ERROR generating initial Excel: {e}")
                import traceback
                traceback.print_exc()
                questions_initial_excel = None
            
            try:
                questions_improved_excel = self.doc_generator.generate_questions_excel(
                    improved, f"questions_improved_{article_id}.xlsx"
                )
                print(f"[STEP 6] Improved Excel: {os.path.basename(questions_improved_excel)}")
            except Exception as e:
                print(f"[STEP 6] ERROR generating improved Excel: {e}")
                import traceback
                traceback.print_exc()
                questions_improved_excel = None
            
            # Upload or save locally
            print(f"\n[STEP 6] Upload to Drive")
            try:
                self.drive_manager.upload_article_package(
                    article, 
                    questions_initial_word, 
                    questions_improved_word,
                    questions_initial_excel,
                    questions_improved_excel
                )
                print(f"[Drive] Upload successful")
                self.state_manager.mark_article_processed(article_id, uploaded=True)
            except Exception as e:
                print(f"[Drive] Upload failed: {e}")
                print(f"[Drive] Files saved locally in data/")
                self.state_manager.mark_article_processed(article_id, uploaded=False)
            
            print(f"\n[Orchestrator] ✓ Article complete: {title[:50]}")
        
        except Exception as e:
            print(f"\n[Orchestrator] ERROR processing article: {e}")
            import traceback
            traceback.print_exc()
            self.state_manager.mark_error(article_id, str(e))
    
    def _upload_master_csv(self):
        """Upload master validated articles CSV to Drive."""
        try:
            print(f"\n[Orchestrator] Uploading master CSV...")
            
            state_df = self.state_manager.load_state()
            validated_df = state_df[state_df['license_status'] == 'approved']
            
            if not validated_df.empty:
                csv_path = self.doc_generator.generate_validated_csv(
                    validated_df.to_dict('records'),
                    filename="validated_articles.csv"
                )
                self.drive_manager.upload_master_csv(csv_path)
                print("[Drive] Master CSV uploaded")
        
        except Exception as e:
            print(f"[Drive] Master CSV upload failed: {e}")
    
    def _find_latest_file(self, pattern: str) -> Optional[str]:
        """Find most recent file matching pattern in data folder."""
        import glob
        
        files = glob.glob(os.path.join(config.BASE_DATA_PATH, pattern))
        if not files:
            return None
        
        # Sort by modification time (newest first)
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    
    def _print_statistics(self):
        """Print final pipeline statistics."""
        stats = self.state_manager.get_statistics()
        
        print(f"\n{'='*70}")
        print(f"PIPELINE STATISTICS")
        print(f"{'='*70}")
        print(f"Total articles:    {stats['total_articles']}")
        print(f"  Validated:       {stats['validated']}")
        print(f"  Rejected:        {stats['rejected']}")
        print(f"  Completed:       {stats['completed']}")
        print(f"  In progress:     {stats['in_progress']}")
        print(f"  Errors:          {stats['errors']}")
        print(f"{'='*70}\n")


# Global orchestrator instance
orchestrator = PipelineOrchestrator()
