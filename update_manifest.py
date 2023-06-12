#!/usr/bin/env python3

from argparse import ArgumentParser
import sys
import xml.etree.ElementTree as ET


class ManifestHandler:
    def __init__(self):
        self.product_manifest = ""
        self.service_manifest = ""
        self.sync_project = ""
        self.view_changes = False
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

    def __parser_args(self):
        args = self.__parser.parse_args()
        self.service_manifest = args.service_manifest
        self.product_manifest = args.product_manifest
        self.sync_project = args.sync_project
        self.view_changes = args.view_changes

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

        tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )

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

