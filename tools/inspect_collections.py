import sys, os, importlib

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
collections_path = os.path.expanduser('~/.ansible/collections')
local_collections = os.path.join(repo_root, 'collections')
print('repo_root=', repo_root)
print('collections_path=', collections_path)
print('local_collections=', local_collections)
for p in (collections_path, local_collections):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

print('\n--- sys.path (first 10) ---')
for i, p in enumerate(sys.path[:10]):
    print(i, p)

try:
    pkg = importlib.import_module('ansible_collections.hashicorp.terraform')
    print('\nImported package: ansible_collections.hashicorp.terraform')
    print('__file__:', getattr(pkg, '__file__', None))
    print('__path__:', getattr(pkg, '__path__', None))
    print('dir(pkg) first 50:', list(dir(pkg))[:50])
except Exception as e:
    print('\nFailed to import package:', type(e).__name__, e)

try:
    import ansible_collections
    print('\nansible_collections module:', getattr(ansible_collections, '__file__', None))
    print('subpackages under ansible_collections:', [name for name in dir(ansible_collections) if not name.startswith('_')][:50])
    h = getattr(ansible_collections, 'hashicorp', None)
    print('\nhashicorp attr:', h)
    if h is not None:
        print('hashicorp __file__:', getattr(h, '__file__', None))
        t = getattr(h, 'terraform', None)
        print('terraform attr:', t)
        if t is not None:
            print('terraform __file__:', getattr(t, '__file__', None))
            print('terraform has plugins?', hasattr(t, 'plugins'))
            if hasattr(t, 'plugins'):
                print('plugins attr:', getattr(t, 'plugins'))
except Exception as e:
    print('\nError during attribute inspection:', type(e).__name__, e)
