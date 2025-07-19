def detect_subscription_type(content):
    """
    自动识别订阅类型：clash 或 shadowrocket
    clash: yaml格式，含proxies: 或 proxy-groups:
    shadowrocket: 普通节点链接（vmess/ss/trojan等）
    """
    if not content:
        return 'unknown'
    if content.startswith('proxies:') or 'proxy-groups:' in content:
        return 'clash'
    # 尝试base64解码
    try:
        import base64
        from urllib.parse import unquote
        cur = content.strip()
        for _ in range(3):
            if any(cur.startswith(proto) for proto in ['vmess://', 'ss://', 'trojan://', 'vless://', 'hysteria2://', 'hysteria://']):
                return 'shadowrocket'
            if cur.startswith('proxies:') or 'proxy-groups:' in cur:
                return 'clash'
            try:
                cur = unquote(cur)
            except Exception:
                pass
            b64 = cur
            missing_padding = len(b64) % 4
            if missing_padding:
                b64 += '=' * (4 - missing_padding)
            try:
                cur = base64.b64decode(b64).decode('utf-8')
            except Exception:
                try:
                    cur = base64.urlsafe_b64decode(b64).decode('utf-8')
                except Exception:
                    break
        if any(cur.startswith(proto) for proto in ['vmess://', 'ss://', 'trojan://', 'vless://', 'hysteria2://', 'hysteria://']):
            return 'shadowrocket'
        if cur.startswith('proxies:') or 'proxy-groups:' in cur:
            return 'clash'
    except Exception:
        pass
    return 'shadowrocket'  # 默认按节点型



from flask import Response
from .models import db, Subscription
import requests
import yaml
from bs4 import BeautifulSoup
from datetime import datetime
import base64
import json
import re

def fetch_subscription(url):
    from .models import Subscription, db
    # 兼容传入Subscription对象或url字符串
    if isinstance(url, Subscription):
        sub = url
        url = sub.url
    else:
        sub = Subscription.query.filter_by(url=url).first()
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        text = resp.text.strip()
        # 自动识别类型并存储
        if sub:
            sub.content = text
            # 自动识别类型
            try:
                sub.type = detect_subscription_type(text)
            except Exception:
                sub.type = 'unknown'
            # 新增：保存原始内容（无论是否已有内容都写入）
            try:
                sub.raw_content = resp.text  # 不strip，保留原始格式
            except Exception:
                pass
            # 新增：更新时间
            from datetime import datetime
            try:
                sub.last_update = datetime.now()
            except Exception:
                pass
            db.session.commit()

        # 1. 先尝试解码base64（自动补全缺失的=，兼容urlsafe编码）

        def recursive_b64_decode(b64text):
            import binascii
            from urllib.parse import unquote
            max_depth = 10
            cur = b64text.strip()
            for _ in range(max_depth):
                # 出现协议头、yaml、json即停止
                if any(cur.startswith(proto) for proto in ['vmess://', 'ss://', 'trojan://', 'vless://', 'hysteria2://', 'hysteria://']) or \
                   cur.startswith('proxies:') or 'proxy-groups:' in cur or cur.lstrip().startswith('{') or cur.lstrip().startswith('['):
                    return cur
                # url解码
                try:
                    cur = unquote(cur)
                except Exception:
                    pass
                # base64补全
                b64 = cur
                missing_padding = len(b64) % 4
                if missing_padding:
                    b64 += '=' * (4 - missing_padding)
                try:
                    cur = base64.b64decode(b64).decode('utf-8')
                except Exception:
                    try:
                        cur = base64.urlsafe_b64decode(b64).decode('utf-8')
                    except Exception:
                        break
            return cur

        # 递归base64解码
        text_decoded = recursive_b64_decode(text)
        # 如果解码后是多行节点，直接分行
        if any(text_decoded.startswith(proto) for proto in ['vmess://', 'ss://', 'trojan://', 'vless://', 'hysteria2://', 'hysteria://']):
            return [line.strip() for line in text_decoded.splitlines() if line.strip()]
        # 如果是yaml
        if text_decoded.startswith('proxies:') or 'proxy-groups:' in text_decoded:
            return text_decoded.splitlines()
        # 如果是json
        try:
            data = json.loads(text_decoded)
            if isinstance(data, dict) and ('proxies' in data or 'proxy-groups' in data):
                return yaml.dump(data, allow_unicode=True).splitlines()
            elif isinstance(data, list):
                lines = []
                for item in data:
                    if isinstance(item, str):
                        lines.append(item)
                    elif isinstance(item, dict):
                        lines.append(yaml.dump(item, allow_unicode=True))
                return [line.strip() for line in lines if line.strip()]
        except Exception:
            pass

        # 兼容HTML页面（部分机场返回网页）
        if text_decoded.lstrip().startswith('<!DOCTYPE html') or text_decoded.lstrip().startswith('<html'):
            soup = BeautifulSoup(text_decoded, 'html.parser')
            code_blocks = soup.find_all(['pre', 'code'])
            lines = []
            for block in code_blocks:
                lines.extend(block.get_text().splitlines())
            links = re.findall(r'(vmess://[^\s]+|ss://[^\s]+|trojan://[^\s]+|vless://[^\s]+|hysteria2://[^\s]+|hysteria://[^\s]+)', text_decoded)
            lines.extend(links)
            return [line.strip() for line in lines if line.strip()]

        # 其他情况按行分割，自动过滤注释和空行
        return [line.strip() for line in text_decoded.splitlines() if line.strip() and not line.strip().startswith('#')]

        # 2. 如果是yaml（以proxies:开头或包含proxy-groups），直接返回全部内容
        if text.startswith('proxies:') or 'proxy-groups:' in text:
            return text.splitlines()

        # 3. 兼容HTML页面（部分机场返回网页）
        if text.lstrip().startswith('<!DOCTYPE html') or text.lstrip().startswith('<html'):
            soup = BeautifulSoup(text, 'html.parser')
            # 提取所有pre/code标签内容
            code_blocks = soup.find_all(['pre', 'code'])
            lines = []
            for block in code_blocks:
                lines.extend(block.get_text().splitlines())
            # 或者直接提取所有vmess/ss等链接
            links = re.findall(r'(vmess://[^\s]+|ss://[^\s]+|trojan://[^\s]+|vless://[^\s]+)', text)
            lines.extend(links)
            return [line.strip() for line in lines if line.strip()]

        # 4. 兼容JSON格式（部分机场返回json数组或对象）
        try:
            data = json.loads(text)
            if isinstance(data, dict) and ('proxies' in data or 'proxy-groups' in data):
                # clash格式
                return yaml.dump(data, allow_unicode=True).splitlines()
            elif isinstance(data, list):
                # 节点数组
                lines = []
                for item in data:
                    if isinstance(item, str):
                        lines.append(item)
                    elif isinstance(item, dict):
                        # 尝试转为clash yaml
                        lines.append(yaml.dump(item, allow_unicode=True))
                return [line.strip() for line in lines if line.strip()]
        except Exception:
            pass

        # 5. 其他情况按行分割，自动过滤注释和空行
        return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith('#')]
    except requests.RequestException as e:
        print(f"网络请求失败: {url} {str(e)}")
        return []
    except Exception as e:
        print(f"解析订阅失败: {url} {str(e)}")
        return []

def filter_nodes(nodes):
    # 示例过滤规则：保留名称包含"VIP"或"Premium"的节点
    filtered = []
    # 支持的所有主流协议
    protocols = [
        'vless://', 'vmess://', 'ss://', 'trojan://', 'hysteria2://', 'hysteria://', 'tuic://', 'socks5://', 'http://', 'https://', 'ssr://'
    ]
    for node in nodes:
        if not isinstance(node, str):
            continue
        # 保留所有主流协议节点
        if any(node.strip().startswith(proto) for proto in protocols):
            filtered.append(node)
    return filtered

def generate_clash_config():
    import yaml
    subscriptions = Subscription.query.filter_by(enabled=True, type='clash').all()
    error_msgs = []
    all_proxies = []
    all_proxy_groups = []
    all_rules = []
    proxy_names = set()
    supported_types = {"vmess", "ss", "trojan", "socks5", "http", "ssr", "snell", "tuic"}
    # 用于后续过滤proxy-group中不存在的proxy
    valid_proxy_names = set()
    # 先处理所有订阅
    for sub in subscriptions:
        try:
            content = sub.content or ''
            # 如果是Clash yaml格式，解析合并
            if content.startswith('proxies:') or 'proxy-groups:' in content:
                try:
                    data = yaml.safe_load(content)
                    if data.get('proxies'):
                        for p in data['proxies']:
                            if p.get('name') not in proxy_names and p.get('type') in supported_types:
                                all_proxies.append(p)
                                proxy_names.add(p.get('name'))
                                valid_proxy_names.add(p.get('name'))
                    if data.get('proxy-groups'):
                        all_proxy_groups.extend(data['proxy-groups'])
                    if data.get('rules'):
                        all_rules.extend(data['rules'])
                except Exception as e:
                    error_msgs.append(f"订阅{sub.name} yaml解析失败: {str(e)}")
                continue
            # 否则按节点处理
            nodes = fetch_subscription(sub.url)
            filtered = filter_nodes(nodes)
            for i, node in enumerate(filtered):
                # vmess节点
                if node.startswith('vmess://'):
                    try:
                        config_str = base64.b64decode(node[8:]).decode('utf-8')
                        config = json.loads(config_str)
                        name = config.get('ps', f'vmess-{i}') or f'vmess-{i}'
                        port = str(config.get('port', '')) or '443'
                        if name not in proxy_names:
                            all_proxies.append({
                                'name': name,
                                'type': 'vmess',
                                'server': config.get('add', ''),
                                'port': port,
                                'uuid': config.get('id', ''),
                                'alterId': config.get('aid', 0),
                                'cipher': 'auto',
                                'udp': True
                            })
                            proxy_names.add(name)
                            valid_proxy_names.add(name)
                    except Exception as e:
                        error_msgs.append(f"节点{i}解析失败: {str(e)}")
                        continue
                else:
                    # 其它协议，全部塞进proxies，type用协议名，server为节点原文
                    proto_match = re.match(r'^(\w+):\/\/', node)
                    proto = proto_match.group(1) if proto_match else 'custom'
                    # 保证name唯一
                    name = f'{proto}-{i}'
                    # 兼容同名情况
                    while name in proxy_names:
                        name = f'{proto}-{i}-{len(proxy_names)}'
                    # 尝试从节点中提取端口
                    port = '443'
                    port_match = re.search(r':(\d+)', node)
                    if port_match:
                        port = port_match.group(1)
                    # socks5/http/ss等类型需要password字段，ss类型还需cipher字段
                    proxy_obj = {
                        'name': name,
                        'type': proto,
                        'server': node,
                        'port': port,
                        'raw': node
                    }
                    if proto in ['socks5', 'http', 'ss', 'ssr', 'trojan']:
                        proxy_obj['password'] = ''
                    if proto == 'ss':
                        proxy_obj['cipher'] = 'aes-128-gcm'  # Clash要求ss必须有cipher字段
                    all_proxies.append(proxy_obj)
                    proxy_names.add(name)
                    valid_proxy_names.add(name)
        except Exception as e:
            error_msgs.append(f"订阅{sub.name}抓取失败: {str(e)}")
    # 过滤proxy-groups中引用了无效proxy的条目，并收集所有有效分组名
    def filter_group_proxies(group):
        # Clash 只支持 proxies/use 字段之一，且必须为非空list
        if 'proxies' in group:
            proxies = group.get('proxies', [])
            if not isinstance(proxies, list) or not proxies:
                return None
            # 只保留有效节点
            group['proxies'] = [p for p in proxies if p in valid_proxy_names or p == 'DIRECT' or p == 'REJECT']
            if not group['proxies']:
                return None
        elif 'use' in group:
            use = group.get('use', [])
            if not isinstance(use, list) or not use:
                return None
        else:
            # 缺少 proxies/use 字段，视为非法
            return None
        return group
    # 过滤掉不合法的proxy-group
    all_proxy_groups = [g for g in (filter_group_proxies(g) for g in all_proxy_groups) if g is not None]
    # 收集所有有效分组名
    group_names = set(g.get('name') for g in all_proxy_groups if g.get('name'))
    # 合并proxy-groups，确保有主组
    if not any(g.get('name') == 'PROXY' for g in all_proxy_groups):
        all_proxy_groups.insert(0, {
            'name': 'PROXY',
            'type': 'select',
            'proxies': [p['name'] for p in all_proxies]
        })
        group_names.add('PROXY')
    # 过滤rules中引用了不存在分组的规则，或自动降级为PROXY
    def fix_rule(rule):
        # 只处理形如 "MATCH,分组名" 的规则
        if isinstance(rule, str) and ',' in rule:
            parts = rule.split(',')
            if len(parts) == 2 and parts[1].strip() not in group_names:
                return f"{parts[0].strip()},PROXY"
        return rule
    fixed_rules = [fix_rule(r) for r in (all_rules or ['GEOIP,CN,DIRECT', 'MATCH,PROXY'])]
    clash_config = {
        'proxies': all_proxies,
        'proxy-groups': all_proxy_groups,
        'rules': fixed_rules
    }
    if not all_proxies:
        msg = 'proxies: []\nproxy-groups:\n- name: PROXY\n  type: select\n  proxies: []\nrules:\n- GEOIP,CN,DIRECT\n- MATCH,PROXY\n'
        if error_msgs:
            msg += '\n'.join(error_msgs)
        return Response(msg, mimetype='text/yaml')
    return Response(yaml.dump(clash_config, allow_unicode=True), mimetype='text/yaml')

def generate_shadowrocket_config():
    subscriptions = Subscription.query.filter_by(enabled=True, type='shadowrocket').all()
    all_nodes = []
    error_msgs = []
    for sub in subscriptions:
        try:
            nodes = fetch_subscription(sub.url)
            filtered = filter_nodes(nodes)
            all_nodes.extend(filtered)
        except Exception as e:
            error_msgs.append(f"订阅{sub.name}抓取失败: {str(e)}")
    config_text = "# Shadowrocket Config\n# Generated at " + datetime.now().isoformat() + "\n\n"
    if not all_nodes:
        config_text += "# 无可用节点\n"
        if error_msgs:
            config_text += '\n'.join(error_msgs)
        return Response(config_text, mimetype='text/plain')
    config_text += "\n".join(all_nodes)
    if error_msgs:
        config_text += "\n# 部分订阅抓取或解析失败:\n" + '\n'.join(error_msgs)
    return Response(config_text, mimetype='text/plain')