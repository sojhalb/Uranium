# Copyright (c) 2017 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

import os.path
import pytest
import copy

from UM.MimeTypeDatabase import MimeType, MimeTypeDatabase
from UM.Resources import Resources

from UM.Settings.ContainerRegistry import ContainerRegistry
from plugins.LocalContainerProvider.LocalContainerProvider import LocalContainerProvider
from UM.PluginRegistry import PluginRegistry

@pytest.fixture
def container_registry(application):
    MimeTypeDatabase.addMimeType(
        MimeType(
            name = "application/x-uranium-definitioncontainer",
            comment = "Uranium Definition Container",
            suffixes = ["def.json"]
        )
    )

    MimeTypeDatabase.addMimeType(
        MimeType(
            name = "application/x-uranium-instancecontainer",
            comment = "Uranium Instance Container",
            suffixes = [ "inst.cfg" ]
        )
    )

    MimeTypeDatabase.addMimeType(
        MimeType(
            name = "application/x-uranium-containerstack",
            comment = "Uranium Container Stack",
            suffixes = [ "stack.cfg" ]
        )
    )

    ContainerRegistry._ContainerRegistry__instance = None # Reset the private instance variable every time
    PluginRegistry.getInstance().removeType("settings_container")

    PluginRegistry.addType("container_provider", LocalContainerProvider)
    PluginRegistry.getInstance().loadPlugin("LocalContainerProvider")
    l = PluginRegistry.getInstance().getPluginObject("LocalContainerProvider")
    ContainerRegistry.getInstance().addProvider(l)

    s = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "Settings"))
    Resources.addSearchPath(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "Settings")))

    empty_container = ContainerRegistry.getInstance().getEmptyInstanceContainer()

    empty_definition_changes_container = copy.deepcopy(empty_container)
    empty_definition_changes_container.setMetaDataEntry("id", "empty_definition_changes")
    empty_definition_changes_container.addMetaDataEntry("type", "definition_changes")
    ContainerRegistry.getInstance().addContainer(empty_definition_changes_container)

    empty_variant_container = copy.deepcopy(empty_container)
    empty_variant_container.setMetaDataEntry("id", "empty_variant")
    empty_variant_container.addMetaDataEntry("type", "variant")
    ContainerRegistry.getInstance().addContainer(empty_variant_container)

    empty_material_container = copy.deepcopy(empty_container)
    empty_material_container.setMetaDataEntry("id", "empty_material")
    empty_material_container.addMetaDataEntry("type", "material")
    ContainerRegistry.getInstance().addContainer(empty_material_container)

    empty_quality_container = copy.deepcopy(empty_container)
    empty_quality_container.setMetaDataEntry("id", "empty_quality")
    empty_quality_container.setName("Not Supported")
    empty_quality_container.addMetaDataEntry("quality_type", "not_supported")
    empty_quality_container.addMetaDataEntry("type", "quality")
    empty_quality_container.addMetaDataEntry("supported", False)
    ContainerRegistry.getInstance().addContainer(empty_quality_container)

    empty_quality_changes_container = copy.deepcopy(empty_container)
    empty_quality_changes_container.setMetaDataEntry("id", "empty_quality_changes")
    empty_quality_changes_container.addMetaDataEntry("type", "quality_changes")
    empty_quality_changes_container.addMetaDataEntry("quality_type", "not_supported")
    ContainerRegistry.getInstance().addContainer(empty_quality_changes_container)

    ContainerRegistry.getInstance().load()



    return ContainerRegistry.getInstance()


benchmark_findContainers_data = [
    { "id": 'basic_definition' }
]

@pytest.mark.parametrize("query_args", benchmark_findContainers_data)
def benchmark_findContainers(benchmark, container_registry, query_args):
    result = benchmark(container_registry.findDefinitionContainers, **query_args)
    assert len(result) >= 1
