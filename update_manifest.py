#!/usr/bin/env python3

from argparse import ArgumentParser
import sys
import xml.etree.ElementTree as ET
import subprocess
from datetime import datetime


class ManifestHandler:
    def __init__(self):
        self.product_manifest = ""
        self.service_manifest = ""
        self.sync_project = ""
        self.view_changes = False
        self.add_project = []
        self.add_entries = False
        self.url = ""
        self.branch = ""
        self.__setup_arg_parser()
        self.__parser_args()
        self.RevisionDict = {}
        self.upstreamDict = {}
        self.path_nameDict = {}

    def __setup_arg_parser(self):
        self.__parser = ArgumentParser()
        self.__parser.add_argument(
            "-p",
            dest="product_manifest",
            help="path to the product manifest",
            action="store",
            required=True,
        )
        self.__parser.add_argument(
            "-s",
            dest="service_manifest",
            help="output file",
            action="store",
            required=True,
        )
        self.__parser.add_argument(
            "-P",
            dest="sync_project",
            help="path to the project to be synced",
            action="store",
            required=False,
        )
        self.__parser.add_argument(
            "-change",
            dest="view_changes",
            help="Visualize the changes without updating the manifest",
            action="store_true",
            required=False
        )
        self.__parser.add_argument(
            "-add",
            dest="add_project",
            nargs='+',
            help="project names to be included int the service_manifest",
            action="store",
            required=False
        )
        self.__parser.add_argument(
            "-full-sync",
            dest="add_entries",
            help="add the missing entries in the service_manifest",
            action="store_true",
            required=False
        )
        self.__parser.add_argument(
            "-u",
            dest="url",
            help="url of the external repository",
            action="store",
            required=False
        )
        self.__parser.add_argument(
            "-b",
            dest="branch",
            help="branch to checkout",
            action="store",
            required=False
        )

    def __parser_args(self):
        args = self.__parser.parse_args()
        self.service_manifest = args.service_manifest
        self.product_manifest = args.product_manifest
        self.sync_project = args.sync_project
        self.view_changes = args.view_changes
        self.add_project = args.add_project
        self.add_entries = args.add_entries
        self.url = args.url
        self.branch = args.branch

    def getRevision(self, projectPath):
        return self.RevisionDict[projectPath]

    def getUpstream(self, projectPath):
        return self.upstreamDict[projectPath]

    def get_path(self, name):
        for key, value in self.path_nameDict.items():
            if value == name:
                return key
        return None

    def initDicts(self, inputXMLFile):
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(inputXMLFile, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            path = ""
            if "path" not in project.attrib:
                path = project.attrib["name"]
            else:
                path = project.attrib["path"]
                self.path_nameDict[path] = project.attrib["name"]
            revision = project.attrib["revision"]
            if "upstream" in project.attrib:
                upstream = project.attrib["upstream"]
                self.upstreamDict[path] = upstream
            self.RevisionDict[path] = revision

    def update_manifest(self):
        if self.url:
            self.add_repo_info()
        if self.add_entries:
            self.add_missing_entries()
        self.initDicts(self.product_manifest)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(self.service_manifest, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            path = ""
            name = project.attrib["name"]
            if "path" not in project.attrib:
                if name in self.path_nameDict.keys():
                    path = name
                if name in self.path_nameDict.values():
                    path = self.get_path(name)
            else:
                path = project.attrib["path"]

            if self.sync_project and path != self.sync_project:
                continue
            if (path in self.RevisionDict.keys()
               or name in self.RevisionDict.keys()):
                if name in self.RevisionDict.keys():
                    path = name
                project.attrib["revision"] = self.getRevision(path)
                if (path not in self.upstreamDict.keys()
                   and "upstream" in project.attrib):
                    project.attrib.pop("upstream", None)
            if (path in self.upstreamDict.keys()
               or name in self.upstreamDict.keys()):
                if name in self.RevisionDict.keys():
                    path = name
                if "upstream" in project.attrib:
                    project.attrib["upstream"] = self.getUpstream(path)
                else:
                    project.set('upstream', self.getUpstream(path))

        for elem in root.iter():
            if (elem.tag == ET.Comment and
                    elem.text and elem.text.startswith("Last Synced on")):
                root.remove(elem)
                break

        current_datetime = datetime.now()
        comment_text = f"Last Synced on: {current_datetime}"
        comment = ET.Comment(comment_text)
        empty_line = ET.ElementTree(ET.Element(None))
        empty_line.getroot().text = "\n\t"

        root.insert(0, empty_line.getroot())

        root.insert(0, comment)

        tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )
        if self.add_project is not None:
            self.add_projects_to_manifest()

    def check_output_manifest(self):
        print("================Begin comparing manifests===================")
        self.initDicts(self.product_manifest)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(self.service_manifest, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            change_log = ""
            path = ""
            name = project.attrib["name"]
            if "path" not in project.attrib:
                if name in self.path_nameDict.keys():
                    path = name
                if name in self.path_nameDict.values():
                    path = self.get_path(name)
            else:
                path = project.attrib["path"]
            if self.sync_project and path != self.sync_project:
                continue
            if (path in self.RevisionDict.keys()
               or name in self.RevisionDict.keys()):
                if name in self.RevisionDict.keys():
                    path = name
                if self.RevisionDict[path] != project.attrib["revision"]:
                    change_log += "{}\t{} => {}\t".format(
                        path, project.attrib["revision"],
                        self.RevisionDict[path])
                    if (path not in self.upstreamDict.keys()
                       and "upstream" in project.attrib):
                        change_log += " upstream deleted"
                elif (path not in self.upstreamDict.keys() and
                        "upstream" in project.attrib):
                    change_log += "{}\t upstream deleted".format(path)
            if (path in self.upstreamDict.keys()
               or name in self.upstreamDict.keys()):
                if name in self.upstreamDict.keys():
                    path = name
                if "upstream" in project.attrib:
                    if self.upstreamDict[path] != project.attrib["upstream"]:
                        if change_log == "":
                            change_log = "{}\t".format(path)
                        change_log += "{}=> {}\t".format(
                            project.attrib["upstream"],
                            self.upstreamDict[path])
                else:
                    if change_log == "":
                        change_log = "{}\t".format(path)
                    change_log += " upstream_added = {}\t".format(
                        self.upstreamDict[path])
            change_log += "\n"
            if change_log != "\n":
                print(change_log, end="")

        print("================ End comparing manifests ===================")

    def add_projects_to_manifest(self):
        product_parser = ET.XMLParser(
                target=ET.TreeBuilder(insert_comments=True))
        product_tree = ET.parse(self.product_manifest, product_parser)
        product_root = product_tree.getroot()

        service_parser = ET.XMLParser(
                target=ET.TreeBuilder(insert_comments=True))
        service_tree = ET.parse(self.service_manifest, service_parser)
        service_root = service_tree.getroot()

        service_project_paths = set()
        for project in service_root.iter("project"):
            path = ""
            if "path" in project.attrib:
                path = project.attrib["path"]
            else:
                path = project.attrib["name"]
            service_project_paths.add(path)

        for project in product_root.iter("project"):
            path = ""
            if "path" in project.attrib:
                path = project.attrib["path"]
            else:
                path = project.attrib["name"]

            flag = True
            if path in self.add_project:
                if path not in service_project_paths:
                    if flag:
                        newline = ET.Element(None)
                        newline.text = "\n\t"
                        flag = False
                    subelement = ET.SubElement(
                            service_root, "project", attrib=project.attrib)
                    subelement.tail = "\n\t"
                    print(f"'{path}' project added to the service_manifest")
                else:
                    print(f"'{path}' is already present in service_manifest")

        service_tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def add_missing_entries(self):
        product_parser = ET.XMLParser(
            target=ET.TreeBuilder(insert_comments=True))
        product_tree = ET.parse(self.product_manifest, product_parser)
        product_root = product_tree.getroot()

        service_parser = ET.XMLParser(
            target=ET.TreeBuilder(insert_comments=True))
        service_tree = ET.parse(self.service_manifest, service_parser)
        service_root = service_tree.getroot()

        service_project_paths = set()
        for project in service_root.iter("project"):
            path = project.attrib.get("path", "")
            name = project.attrib.get("name", "")
            if path:
                service_project_paths.add(path)
            elif name:
                service_project_paths.add(name)

        for project in product_root.iter("project"):
            path = project.attrib.get("path", "")
            name = project.attrib.get("name", "")
            if (path not in service_project_paths and
               name not in service_project_paths):
                subelement = ET.SubElement(service_root,
                                           "project", attrib=project.attrib)
                subelement.tail = "\n\t"
                if path:
                    print(f"'{path}' project added to the service_manifest")
                elif name:
                    print(f"'{name}' project added to the service_manifest")

        service_tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def add_repo_info(self):
        url = self.url
        branch = ""
        if self.branch:
            branch = self.branch
        else:
            print("Defaulting to master branch")
            branch = "master"

        repo_name = url.split("/")[-1].split(".")[0]
        command = ["git", "ls-remote", "--heads", url, branch]

        try:
            output = subprocess.check_output(command).decode("utf-8")
            revision = output.split()[0]
        except subprocess.CalledProcessError:
            return None, None

        service_parser = ET.XMLParser(
                target=ET.TreeBuilder(insert_comments=True))
        service_tree = ET.parse(self.service_manifest, service_parser)
        service_root = service_tree.getroot()

        for project in service_root.iter("project"):
            path = project.attrib.get("path")
            if path and path == repo_name:
                old_revision = project.attrib["revision"]
                project.attrib["revision"] = revision
                print("Project for given url is found and revision is updated")
                print(f"'{path}'    '{old_revision}' => '{revision}'")
                break
        service_tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )


def main():
    manifest_handler = ManifestHandler()
    if manifest_handler.view_changes:
        print("Displaying the changes occured in the service_manifest")
        manifest_handler.check_output_manifest()
    else:
        manifest_handler.check_output_manifest()
        manifest_handler.update_manifest()
        manifest_handler.check_output_manifest()
    sys.exit(0)


if __name__ == "__main__":
    main()
