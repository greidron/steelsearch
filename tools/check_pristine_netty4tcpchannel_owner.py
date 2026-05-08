#!/usr/bin/env python3
import io
import json
import sys
import tarfile
import zipfile
from pathlib import Path

MEMBER = 'org/opensearch/transport/netty4/Netty4TcpChannel.class'
MODULE_SUFFIX = '/modules/transport-netty4/transport-netty4-client-3.7.0-SNAPSHOT.jar'
LIB_SUFFIX = '/lib/opensearch-3.7.0-SNAPSHOT.jar'


def tar_jar_has(tar_path: Path, suffix: str) -> bool:
    with tarfile.open(tar_path, 'r:gz') as tf:
        name = next(n for n in tf.getnames() if n.endswith(suffix))
        data = tf.extractfile(name).read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return MEMBER in zf.namelist()


def jar_has(jar_path: Path) -> bool:
    with zipfile.ZipFile(jar_path) as zf:
        return MEMBER in zf.namelist()


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_pristine_netty4tcpchannel_owner.py <pristine-tar.gz> <install-module-jar> <install-lib-jar>', file=sys.stderr)
        return 2
    tar_path = Path(sys.argv[1])
    install_module = Path(sys.argv[2])
    install_lib = Path(sys.argv[3])
    pristine_module_has = tar_jar_has(tar_path, MODULE_SUFFIX)
    pristine_lib_has = tar_jar_has(tar_path, LIB_SUFFIX)
    install_module_has = jar_has(install_module)
    install_lib_has = jar_has(install_lib)
    result = 'inconclusive'
    if pristine_module_has and not pristine_lib_has and install_module_has and install_lib_has:
        result = 'pristine_tarball_shows_module_only_owner_so_current_install_tree_dual_jar_presence_is_not_baseline'
    print(json.dumps({
        'pristine_tarball': str(tar_path),
        'pristine_module_jar_has_netty4tcpchannel': pristine_module_has,
        'pristine_lib_jar_has_netty4tcpchannel': pristine_lib_has,
        'install_module_jar_has_netty4tcpchannel': install_module_has,
        'install_lib_jar_has_netty4tcpchannel': install_lib_has,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
