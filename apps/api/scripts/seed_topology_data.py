#!/usr/bin/env python3
"""
Neo4j 토폴로지 시드 데이터 생성 스크립트

사용법:
    python scripts/seed_topology_data.py --tenant-id default
"""

import argparse
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_settings
from neo4j import GraphDatabase


class Neo4jTopologySeeder:
    """Neo4j 토폴로지 시드 데이터 생성기"""
    
    def __init__(self, settings):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    
    def seed_topology(self, tenant_id="default"):
        """
        토폴로지 데이터 시드 생성
        
        노드: 7개 (Load Balancer, API Gateway, Web Server, App Service, Redis, PostgreSQL, NFS)
        관계: 8개
        """
        with self.driver.session() as session:
            print(f"Seeding topology data for tenant: {tenant_id}")
            
            # 노드 생성
            nodes = [
                {"name": "loadbalancer", "type": "network", "baseline_load": 50.0},
                {"name": "api-gateway", "type": "service", "baseline_load": 45.0},
                {"name": "web-server", "type": "server", "baseline_load": 60.0},
                {"name": "app-service", "type": "service", "baseline_load": 55.0},
                {"name": "cache-redis", "type": "db", "baseline_load": 30.0},
                {"name": "db-postgres", "type": "db", "baseline_load": 65.0},
                {"name": "storage-nfs", "type": "storage", "baseline_load": 40.0},
            ]
            
            # 기존 데이터 삭제 (갱신을 위해)
            session.run("""
                MATCH (n {tenant_id: $tenant_id})
                DETACH DELETE n
            """, {"tenant_id": tenant_id})
            
            # 노드 생성
            session.run("""
                UNWIND $nodes AS node
                CREATE (n)
                SET n = node
                SET n.tenant_id = $tenant_id
            """, {
                "nodes": nodes,
                "tenant_id": tenant_id
            })
            print(f"✓ Created {len(nodes)} nodes")
            
            # 관계 생성
            session.run("""
                MATCH (lb:Network {name: "loadbalancer", tenant_id: $tenant_id})
                MATCH (gw:Service {name: "api-gateway", tenant_id: $tenant_id})
                MATCH (ws:Server {name: "web-server", tenant_id: $tenant_id})
                MATCH (asv:Service {name: "app-service", tenant_id: $tenant_id})
                MATCH (redis:Db {name: "cache-redis", tenant_id: $tenant_id})
                MATCH (pg:Db {name: "db-postgres", tenant_id: $tenant_id})
                MATCH (nfs:Storage {name: "storage-nfs", tenant_id: $tenant_id})
                
                // Load Balancer → API Gateway (Traffic)
                MERGE (lb)-[:TRAFFIC {baseline_traffic: 1000.0}]->(gw)
                
                // API Gateway → Web Server, Redis (Traffic, Dependency)
                MERGE (gw)-[:TRAFFIC {baseline_traffic: 800.0}]->(ws)
                MERGE (gw)-[:DEPENDS_ON {baseline_traffic: 400.0}]->(redis)
                
                // Web Server → App Service, PostgreSQL (Traffic, Dependency)
                MERGE (ws)-[:TRAFFIC {baseline_traffic: 600.0}]->(asv)
                MERGE (ws)-[:DEPENDS_ON {baseline_traffic: 500.0}]->(pg)
                
                // App Service → Redis, PostgreSQL (Dependency)
                MERGE (asv)-[:DEPENDS_ON {baseline_traffic: 350.0}]->(redis)
                MERGE (asv)-[:DEPENDS_ON {baseline_traffic: 450.0}]->(pg)
                
                // PostgreSQL → NFS Storage (Dependency)
                MERGE (pg)-[:DEPENDS_ON {baseline_traffic: 300.0}]->(nfs)
            """, {"tenant_id": tenant_id})
            print("✓ Created 8 relationships")
            
            # 검증: 노드 수 확인
            node_count = session.run("""
                MATCH (n {tenant_id: $tenant_id})
                RETURN count(n) AS count
            """, {"tenant_id": tenant_id}).single()["count"]
            print(f"✓ Total nodes: {node_count}")
            
            # 검증: 관계 수 확인
            rel_count = session.run("""
                MATCH ()-[r]->() 
                WHERE r.baseline_traffic IS NOT NULL
                RETURN count(r) AS count
            """).single()["count"]
            print(f"✓ Total relationships: {rel_count}")
            
            print(f"\n✅ Topology seeding completed for tenant: {tenant_id}")
    
    def close(self):
        self.driver.close()


def main():
    parser = argparse.ArgumentParser(
        description="Seed Neo4j topology data"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=get_settings().default_tenant_id,
        help="Tenant ID (default: DEFAULT_TENANT_ID env)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all topology data before seeding"
    )
    args = parser.parse_args()
    
    settings = get_settings()
    seeder = Neo4jTopologySeeder(settings)
    
    try:
        seeder.seed_topology(tenant_id=args.tenant_id)
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
