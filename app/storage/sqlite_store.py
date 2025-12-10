import sqlite3
import json
import asyncio
import aiosqlite
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.state import WorkflowRun, WorkflowState, NodeExecution, NodeStatus

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """SQLite-based storage for workflow graphs and runs"""
    
    def __init__(self, db_path: str = "workflow.db"):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Create graphs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS graphs (
                    graph_id TEXT PRIMARY KEY,
                    definition TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create workflow_runs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    initial_state TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    current_node TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (graph_id) REFERENCES graphs (graph_id)
                )
            """)
            
            # Create node_executions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS node_executions (
                    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error TEXT,
                    output TEXT,
                    logs TEXT,
                    FOREIGN KEY (run_id) REFERENCES workflow_runs (run_id)
                )
            """)
            
            await db.commit()
        
        self._initialized = True
        logger.info("Database initialized successfully")
    
    async def save_graph(self, graph_id: str, definition: Dict[str, Any]) -> None:
        """Save a workflow graph definition"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO graphs (graph_id, definition) VALUES (?, ?)",
                (graph_id, json.dumps(definition))
            )
            await db.commit()
        
        logger.info(f"Saved graph {graph_id}")
    
    async def get_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Get a workflow graph definition"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT definition FROM graphs WHERE graph_id = ?", 
                (graph_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                return None
    
    async def list_graphs(self) -> List[Dict[str, Any]]:
        """List all workflow graphs"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT graph_id, created_at FROM graphs ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "graph_id": row[0],
                        "created_at": row[1]
                    }
                    for row in rows
                ]
    
    async def save_workflow_run(self, workflow_run: WorkflowRun) -> None:
        """Save a workflow run"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Save main workflow run
            await db.execute("""
                INSERT OR REPLACE INTO workflow_runs 
                (run_id, graph_id, status, initial_state, current_state, 
                 current_node, error, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_run.run_id,
                workflow_run.graph_id,
                workflow_run.status.value,
                workflow_run.initial_state.model_dump_json(),
                workflow_run.current_state.model_dump_json(),
                workflow_run.current_node,
                workflow_run.error,
                workflow_run.created_at.isoformat(),
                workflow_run.completed_at.isoformat() if workflow_run.completed_at else None
            ))
            
            # Delete existing node executions for this run
            await db.execute(
                "DELETE FROM node_executions WHERE run_id = ?",
                (workflow_run.run_id,)
            )
            
            # Save node executions
            for execution in workflow_run.node_executions:
                await db.execute("""
                    INSERT INTO node_executions 
                    (run_id, node_id, status, started_at, completed_at, error, output, logs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow_run.run_id,
                    execution.node_id,
                    execution.status.value,
                    execution.started_at.isoformat() if execution.started_at else None,
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    execution.error,
                    json.dumps(execution.output) if execution.output else None,
                    json.dumps(execution.logs) if execution.logs else None
                ))
            
            await db.commit()
        
        logger.info(f"Saved workflow run {workflow_run.run_id}")
    
    async def get_workflow_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Get a workflow run by ID"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get main workflow run
            async with db.execute("""
                SELECT graph_id, status, initial_state, current_state, 
                       current_node, error, created_at, completed_at
                FROM workflow_runs WHERE run_id = ?
            """, (run_id,)) as cursor:
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Get node executions
                async with db.execute("""
                    SELECT node_id, status, started_at, completed_at, error, output, logs
                    FROM node_executions WHERE run_id = ?
                    ORDER BY started_at
                """, (run_id,)) as exec_cursor:
                    exec_rows = await exec_cursor.fetchall()
                
                # Reconstruct workflow run
                node_executions = []
                for exec_row in exec_rows:
                    execution = NodeExecution(
                        node_id=exec_row[0],
                        status=NodeStatus(exec_row[1]),
                        started_at=datetime.fromisoformat(exec_row[2]) if exec_row[2] else None,
                        completed_at=datetime.fromisoformat(exec_row[3]) if exec_row[3] else None,
                        error=exec_row[4],
                        output=json.loads(exec_row[5]) if exec_row[5] else None,
                        logs=json.loads(exec_row[6]) if exec_row[6] else []
                    )
                    node_executions.append(execution)
                
                workflow_run = WorkflowRun(
                    run_id=run_id,
                    graph_id=row[0],
                    status=NodeStatus(row[1]),
                    initial_state=WorkflowState.model_validate_json(row[2]),
                    current_state=WorkflowState.model_validate_json(row[3]),
                    current_node=row[4],
                    error=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    node_executions=node_executions
                )
                
                return workflow_run
    
    async def list_workflow_runs(self, graph_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflow runs, optionally filtered by graph_id"""
        await self.initialize()
        
        query = "SELECT run_id, graph_id, status, created_at, completed_at FROM workflow_runs"
        params = ()
        
        if graph_id:
            query += " WHERE graph_id = ?"
            params = (graph_id,)
        
        query += " ORDER BY created_at DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                return [
                    {
                        "run_id": row[0],
                        "graph_id": row[1],
                        "status": row[2],
                        "created_at": row[3],
                        "completed_at": row[4]
                    }
                    for row in rows
                ]
    
    async def delete_graph(self, graph_id: str) -> bool:
        """Delete a workflow graph and all associated runs"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # First, get all runs for this graph
            async with db.execute(
                "SELECT run_id FROM workflow_runs WHERE graph_id = ?",
                (graph_id,)
            ) as cursor:
                run_ids = [row[0] for row in await cursor.fetchall()]
            
            # Delete node executions for these runs
            for run_id in run_ids:
                await db.execute(
                    "DELETE FROM node_executions WHERE run_id = ?",
                    (run_id,)
                )
            
            # Delete workflow runs
            await db.execute(
                "DELETE FROM workflow_runs WHERE graph_id = ?",
                (graph_id,)
            )
            
            # Delete the graph
            result = await db.execute(
                "DELETE FROM graphs WHERE graph_id = ?",
                (graph_id,)
            )
            
            await db.commit()
            
            return result.rowcount > 0
    
    async def delete_workflow_run(self, run_id: str) -> bool:
        """Delete a specific workflow run"""
        await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Delete node executions
            await db.execute(
                "DELETE FROM node_executions WHERE run_id = ?",
                (run_id,)
            )
            
            # Delete workflow run
            result = await db.execute(
                "DELETE FROM workflow_runs WHERE run_id = ?",
                (run_id,)
            )
            
            await db.commit()
            
            return result.rowcount > 0