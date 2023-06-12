
#!/usr/bin/env python3

from argparse import ArgumentParser
import sys
import xml.etree.ElementTree as ET


class ManifestHandler:
    def __init__(self):
        self.product_manifest = ""
        self.service_manifest = ""
        self.__setup_arg_parser()
        self.__parser_args()
        self.RevisionDict = {}
        self.upstreamDict = {}

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

    def __parser_args(self):
        args = self.__parser.parse_args()
        self.service_manifest = args.service_manifest
        self.product_manifest = args.product_manifest

    def getRevision(self, projectPath):
        return self.RevisionDict[projectPath]

    def getUpstream(self, projectPath):
        return self.upstreamDict[projectPath]

    def update_manifest(self):
        self.initDicts(self.product_manifest)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(self.service_manifest, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            path = project.attrib["path"]
            if path in self.RevisionDict.keys():
                project.attrib["revision"] = self.getRevision(path)
                if path not in self.upstreamDict.keys():
                    if "upstream" in project.attrib:
                        project.attrib.pop("upstream", None)
            if path in self.upstreamDict.keys():
                if "upstream" in project.attrib:
                    project.attrib["upstream"] = self.getUpstream(path)
                else:
                    project.set('upstream', self.getUpstream(path))

        tree.write(
            self.service_manifest,
            xml_declaration=True,
            encoding="UTF-8"
        )

    def initDicts(self, inputXMLFile):
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(inputXMLFile, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            path = project.attrib["path"]
            revision = project.attrib["revision"]
            if "upstream" in project.attrib:
                upstream = project.attrib["upstream"]
                self.upstreamDict[path] = upstream
            self.RevisionDict[path] = revision

    def check_output_manifest(self):
        print("================Begin comparing manifests===================")
        self.initDicts(self.product_manifest)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(self.service_manifest, parser)
        root = tree.getroot()
        for project in root.iter("project"):
            change_log = ""
            path = project.attrib["path"]
            if path in self.RevisionDict.keys():
                if self.RevisionDict[path] != project.attrib["revision"]:
                    change_log += "{}\t{} => {}\t".format(
                            path, project.attrib["revision"],
                            self.RevisionDict[path])
                    if path not in self.upstreamDict.keys():
                        if "upstream" in project.attrib:
                            change_log += " upstream deleted"
                elif path not in self.upstreamDict.keys():
                    if "upstream" in project.attrib:
                        change_log += "{}\t upstream deleted".format(path)
            if path in self.upstreamDict.keys():
                if "upstream" in project.attrib:
                    if self.upstreamDict[path] != project.attrib["upstream"]:
                        if change_log == "":
                            change_log = "{}\t".format(path)
                        change_log += "{} => {}\t".format(
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
    manifest_handler.check_output_manifest()
    manifest_handler.update_manifest()
    manifest_handler.check_output_manifest()
    sys.exit(0)


if __name__ == "__main__":
    main()
