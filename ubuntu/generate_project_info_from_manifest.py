from __future__ import print_function
import argparse
import collections
import os
import requests
from lxml import etree
from helpers import logger


def get_file_data_api_response(project, revision, file_name):
    params = {'project': project, 'revision': revision,
                  'file': file_name}
    url = 'https://{}/api/v1/get_file_data/'.format('aim.qualcomm.com')
    try:
        return requests.get(url, params=params, verify=False)
    except Exception as e:
        raise e


def parse_from_string(xml_string):
    from builtins import bytes
    if isinstance(xml_string, str):
        xml_string = bytes(xml_string, encoding='utf-8')
    return etree.fromstring(xml_string)


def etree_to_dict(node):
    """
    Convert an elementtree to dict
    """
    d = {node.tag: {} if node.attrib else None}
    children = list(node)

    if children:
        dd = collections.defaultdict(list)
        for dc in map(etree_to_dict, children):
            for key, val in list(dc.items()):
                dd[str(key)].append(val)
        d = {
            node.tag: {str(key): val[0] if len(val) == 1 else val
                       for key, val in list(dd.items())}}
    if node.attrib:
        d[node.tag].update((str(k), v) for k, v in list(node.attrib.items()))
    if node.text:
        text = node.text.strip()
        if children or node.attrib:
            d[node.tag]['#text'] = text
        else:
            d[node.tag] = text
    return d


def get_file_data_as_dict(project, revision, filename='default.xml'):
    """
    get the file data and convert to dict
    """
    response = get_file_data_api_response(project, revision, filename)
    try:
        result = response.json()
        json_data = result.get('file_data').encode('utf-8')
        data_json = etree_to_dict(parse_from_string(json_data))
        return data_json
    except Exception as e:
        raise e


def write_to_file(workspace, projects, out_path=None):
    if not out_path:
        out_path = os.path.join(workspace,'project_info.txt')
    with open(out_path, 'w') as f:
        for project in projects:
            prj_path = project.get('path')
            prj_ship_val = project.get('x-ship')
            if prj_ship_val == 'oss':
                prj_ship_val = 'oss'
            else:
                prj_ship_val = 'prop'
            f.write("{}\t{}\n".format(prj_path, prj_ship_val))
    return


def get_elements(xml_root, element_name):
    return xml_root.findall(element_name)


def create_project_info_file(workspace, project, revision, au, group, out_path=None):
    if au:
        revision = au
    manifest_file  = os.path.join(workspace, '.repo/manifests/default.xml')
    if os.path.exists(manifest_file):
        xml_root = etree.parse(manifest_file)
        xml_root.findall('project')
        projects = get_elements(xml_root.getroot(), 'project')
        if group:
            logger.info(get_comp_tag_for_groups(projects, group))
        else:
            write_to_file(workspace, projects, out_path)
    else:
        mf_data = get_file_data_as_dict(project, revision)
        projects = mf_data['manifest']['project']
        if group:
            logger.info(get_comp_tag_for_groups(projects, group))
        else:
            write_to_file(workspace, projects, out_path)
    return


def get_comp_tag_for_groups(projects, group):
    for project in projects:
        if project.get('groups') == group:
            if project.get('x-component-tag'):
                return project.get('x-component-tag').replace('refs/tags/', '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace_tree')
    parser.add_argument('manifest_project')
    parser.add_argument('manifest_branch')
    parser.add_argument('--au')
    parser.add_argument('--group')
    parser.add_argument('--info_out', required=False, help='Path to keep package_info.txt, default <workspace>/project_info.txt')
    args = parser.parse_args()
    create_project_info_file(args.workspace_tree,
        args.manifest_project, args.manifest_branch, args.au, args.group, args.info_out)


if __name__ == "__main__":
    main()
