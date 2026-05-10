from app import create_app
import json

app = create_app()
routes = []

with app.app_context():
    for rule in app.url_map.iter_rules():
        # Filter out static routes for clarity
        if 'static' in rule.endpoint:
            continue
            
        routes.append({
            "rule": rule.rule,
            "methods": list(rule.methods),
            "endpoint": rule.endpoint
        })

print(json.dumps(routes, indent=2))
