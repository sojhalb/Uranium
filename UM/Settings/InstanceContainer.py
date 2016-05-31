# Copyright (c) 2016 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

import configparser
import io

from UM.Signal import Signal, signalemitter
from UM.PluginObject import PluginObject
from UM.Logger import Logger

import UM.Settings.ContainerRegistry

from . import ContainerInterface
from . import SettingInstance
from . import SettingRelation

class InvalidInstanceError(Exception):
    pass

class IncorrectInstanceVersionError(Exception):
    pass

class DefinitionNotFoundError(Exception):
    pass

##  A container for SettingInstance objects.
#
#
@signalemitter
class InstanceContainer(ContainerInterface.ContainerInterface, PluginObject):
    Version = 2

    ##  Constructor
    #
    #   \param container_id A unique, machine readable/writable ID for this container.
    def __init__(self, container_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._id = str(container_id)
        self._name = container_id
        self._definition = None
        self._metadata = {}
        self._instances = {}

        self._dirty = False

    ##  \copydoc ContainerInterface::getId
    #
    #   Reimplemented from ContainerInterface
    def getId(self):
        return self._id

    id = property(getId)

    ##  \copydoc ContainerInterface::getName
    #
    #   Reimplemented from ContainerInterface
    def getName(self):
        return self._name

    name = property(getName)

    nameChanged = Signal()

    def setName(self, name):
        if name != self._name:
            self._name = name
            self._dirty = True
            self.nameChanged.emit()

    ##  \copydoc ContainerInterface::getMetaData
    #
    #   Reimplemented from ContainerInterface
    def getMetaData(self):
        return self._metadata

    metaData = property(getMetaData)
    metaDataChanged = Signal()

    def setMetaData(self, metadata):
        if metadata != self._metadata:
            self._metadata = metadata
            self.metaDataChanged.emit()

    ##  \copydoc ContainerInterface::getMetaDataEntry
    #
    #   Reimplemented from ContainerInterface
    def getMetaDataEntry(self, entry, default = None):
        return self._metadata.get(entry, default)

    def addMetaDataEntry(self, key, value):
        if key not in self._metadata:
            self._metadata[key] = value
            self._dirty = True
        else:
            Logger.log("w", "Meta data with key %s was already added.", key)

    ##  Check if this container is dirty, that is, if it changed from deserialization.
    def isDirty(self):
        return self._dirty

    ##  \copydoc ContainerInterface::getProperty
    #
    #   Reimplemented from ContainerInterface
    def getProperty(self, key, property_name):
        if key in self._instances:
            try:
                return getattr(self._instances[key], property_name)
            except AttributeError:
                pass

        return None

    ##  \copydoc ContainerInterface::hasProperty
    #
    #   Reimplemented from ContainerInterface.
    def hasProperty(self, key, property_name):
        return key in self._instances and hasattr(self._instances[key], property_name)

    ##  Set the value of a property of a SettingInstance.
    #
    #   This will set the value of the specified property on the SettingInstance corresponding to key.
    #   If no instance has been created for the specified key, a new one will be created and inserted
    #   into this instance.
    #
    #   \param key \type{string} The key of the setting to set a property of.
    #   \param property_name \type{string} The name of the property to set.
    #   \param property_value The new value of the property.
    #   \param container The container to use for retrieving values when changing the property triggers property updates. Defaults to None, which means use the current container.
    #
    #   \note If no definition container is set for this container, new instances cannot be created and this method will do nothing.
    def setProperty(self, key, property_name, property_value, container = None):
        if key not in self._instances:
            if not self._definition:
                Logger.log("w", "Tried to set value of setting %s that has no instance in container %s and unable to create a new instance", key, repr(self))
                return

            setting_definition = self._definition.findDefinitions(key = key)
            if not setting_definition:
                Logger.log("w", "Tried to set value of setting %s that has no instance in container %s and unable to create a new instance", key, repr(self))
                return

            instance = SettingInstance.SettingInstance(setting_definition[0], self)
            instance.propertyChanged.connect(self.propertyChanged)
            self._instances[instance.definition.key] = instance

        Logger.log("d", "Set property %s of setting %s in container %s to value %s", property_name, key, self._id, property_value)
        self._instances[key].setProperty(property_name, property_value, container)

        self._dirty = True

    propertyChanged = Signal()

    ##  \copydoc ContainerInterface::serialize
    #
    #   Reimplemented from ContainerInterface
    def serialize(self):
        parser = configparser.ConfigParser(interpolation = None, empty_lines_in_values = False)

        if not self._definition:
            Logger.log("e", "Tried to serialize an instance container without definition, this is not supported")
            return ""

        parser["general"] = {}
        parser["general"]["version"] = str(self.Version)
        parser["general"]["name"] = str(self._name)
        parser["general"]["definition"] = str(self._definition.getId())

        parser["metadata"] = {}
        for key, value in self._metadata.items():
            parser["metadata"][key] = str(value)

        parser["values"] = {}
        for key, instance in self._instances.items():
            if instance.state != SettingInstance.InstanceState.User:
                continue

            try:
                parser["values"][key] = str(instance.value)
            except AttributeError:
                pass

        stream = io.StringIO()
        parser.write(stream)
        return stream.getvalue()

    ##  \copydoc ContainerInterface::deserialize
    #
    #   Reimplemented from ContainerInterface
    def deserialize(self, serialized):
        parser = configparser.ConfigParser(interpolation = None, empty_lines_in_values = False)
        parser.read_string(serialized)

        if not "general" in parser or not "version" in parser["general"] or not "definition" in parser["general"]:
            raise InvalidInstanceError("Missing required section 'general' or 'version' property")

        if parser["general"].getint("version") != self.Version:
            raise IncorrectInstanceVersionError("Reported version {0} but expected version {1}".format(parser["general"].getint("version"), self.Version))

        self._name = parser["general"].get("name", self._id)

        definition_id = parser["general"]["definition"]
        definitions = UM.Settings.ContainerRegistry.getInstance().findDefinitionContainers(id = definition_id)
        if not definitions:
            raise DefinitionNotFoundError("Could not find definition {0} required for instance {1}".format(definition_id, self._id))
        self._definition = definitions[0]

        if "metadata" in parser:
            self._metadata = dict(parser["metadata"])

        if "values" in parser:
            for key, value in parser["values"].items():
                self.setProperty(key, "value", value, self._definition)

        self._dirty = False

    ##  Find instances matching certain criteria.
    #
    #   \param kwargs \type{dict} A dictionary of keyword arguments with key-value pairs that should match properties of the instances.
    def findInstances(self, **kwargs):
        result = []
        for setting_key, instance in self._instances.items():
            for key, value in kwargs.items():
                if not hasattr(instance, key) or getattr(instance, key) != value:
                    break
            else:
                result.append(instance)

        return result

    ##  Get an instance by key
    #
    def getInstance(self, key):
        if key in self._instances:
            return self._instances[key]

        return None

    ##  Add a new instance to this container.
    def addInstance(self, instance):
        key = instance.definition.key
        if key in self._instances:
            return

        instance.propertyChanged.connect(self.propertyChanged)
        self._instances[key] = instance

    ##  Remove an instance from this container.
    def removeInstance(self, key):
        if key not in self._instances:
            return

        instance = self._instances[key]
        del self._instances[key]
        instance.propertyChanged.emit(key, "value")

        self._dirty = True

        # Notify listeners of changed properties for all related properties
        for relation in instance.definition.relations:
            if relation.type == SettingRelation.RelationType.RequiresTarget:
                continue

            self.propertyChanged.emit(relation.target.key, relation.role)


    ##  Get the DefinitionContainer used for new instance creation.
    def getDefinition(self):
        return self._definition

    ##  Set the DefinitionContainer to use for new instance creation.
    #
    #   Since SettingInstance needs a SettingDefinition to work properly, we need some
    #   way of figuring out what SettingDefinition to use when creating a new SettingInstance.
    def setDefinition(self, definition):
        self._definition = definition

    def __lt__(self, other):
        own_weight = self.getMetaDataEntry("weight")
        other_weight = self.getMetaDataEntry("weight")

        if own_weight and other_weight:
            return own_weight < other_weight

        return self._name < other.name
