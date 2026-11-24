"""Compute execution accuracy by projecting pred result to gold columns."""
import json, sqlite3, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_gold_columns(gold_sql):
    """Extract column names from gold SQL using sqlparse."""
    import sqlparse
    parsed = sqlparse.parse(gold_sql)[0]
    fields = []
    for token in parsed.tokens:
        if isinstance(token, sqlparse.sql.IdentifierList):
            for ident in token.get_identifiers():
                val = ident.value.replace('`', '')
                # Remove table prefix (T1., T2., etc)
                val = re.sub(r'T\d+\.', '', val)
                # Remove AS alias
                parts = val.split(' AS ')
                fields.append(parts[-1].strip().lower())
            break
    return fields


def eval_accuracy(pred_results, gold_path, db_path):
    """Compute execution accuracy for a list of pred results."""
    with open(gold_path) as f:
        gold_lines = [l.strip().split('\t') for l in f if l.strip()]
    
    total, correct = 0, 0
    by_difficulty = {'easy': [0, 0], 'medium': [0, 0], 'hard': [0, 0], 'extra': [0, 0]}
    
    conn = sqlite3.connect(db_path)
    
    for r in pred_results:
        if r.get('s') != 'ok':
            continue
        idx = r['q']
        if idx >= len(gold_lines):
            continue
        g_str = gold_lines[idx][0]
        
        try:
            # Execute pred SQL
            cur = conn.cursor()
            cur.execute(r['sql'])
            p_cols = [d[0].lower().replace('`', '') for d in cur.description]
            p_cols = [re.sub(r't\d+\.', '', c) for c in p_cols]
            p_rows = cur.fetchall()
            
            # Execute gold SQL
            cur.execute(g_str)
            g_cols = [d[0].lower().replace('`', '') for d in cur.description]
            g_cols = [re.sub(r't\d+\.', '', c) for c in g_cols]
            g_rows = cur.fetchall()
            
            # Build result maps only for gold columns
            pred_map = {}
            for gi, gc in enumerate(g_cols):
                if gc in p_cols:
                    pi = p_cols.index(gc)
                    vals = sorted([row[pi] for row in p_rows])
                else:
                    vals = []
                pred_map[gc] = vals
            
            gold_map = {}
            for gi, gc in enumerate(g_cols):
                vals = sorted([row[gi] for row in g_rows])
                gold_map[gc] = vals
            
            match = (pred_map == gold_map)
            total += 1
            if match:
                correct += 1
            
        except Exception as e:
            pass  # SQL execution failed = incorrect
    
    conn.close()
    acc = correct / total if total > 0 else 0
    return {'correct': correct, 'total': total, 'accuracy': acc}


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    gold_path = os.path.join(base_dir, 'data', 'gold_example_dusql.txt')
    db_path = os.path.join(base_dir, 'data', 'internet.db')
    
    # Test with v4pro data
    for model, raw_file in [
        ('deepseek-v4-pro', 'output/20260714_173201/v4pro_raw.json'),
        ('deepseek-v4-flash', 'output/20260714_194007/flash_native_raw.json'),
    ]:
        path = os.path.join(base_dir, raw_file)
        if not os.path.exists(path):
            print(f'{model}: FILE NOT FOUND {raw_file}')
            continue
        with open(path) as f:
            data = json.load(f)
        
        r = eval_accuracy(data, gold_path, db_path)
        print(f'{model}: {r["correct"]}/{r["total"]} = {r["accuracy"]:.1%}')
