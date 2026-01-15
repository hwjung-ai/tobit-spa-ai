MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS cnt ORDER BY cnt DESC
