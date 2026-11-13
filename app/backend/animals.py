"""Broad organism categories; legacy species configurations remain readable."""
ANIMAL_CLASS_IDS={'Bird':14,'Cat':15,'Dog':16,'Horse':17,'Sheep':18,'Cow':19,'Elephant':20,'Bear':21,'Zebra':22,'Giraffe':23}
ANIMAL_COLORS={name:'#e9a7cc' for name in ANIMAL_CLASS_IDS}
ORGANISM_CATEGORIES=('Land Mammals','Aquatic/Marine Animals','Reptilian Creatures','Humans','Unclassified Wildlife')
LAND_MAMMALS=[name for name in ANIMAL_CLASS_IDS if name!='Bird']

def organism_categories(config):
    targets=config.get('classes',[])
    if 'Wildlife' not in targets and 'Living Organisms' not in targets:return []
    if 'organismCategories' in config:
        selected=config['organismCategories']
        if not isinstance(selected,list) or not selected or any(c not in ORGANISM_CATEGORIES for c in selected):raise ValueError('Choose at least one supported organism category.')
        return list(dict.fromkeys(selected))
    groups=['Land Mammals','Unclassified Wildlife']
    if 'Living Organisms' in targets:groups.append('Humans')
    return groups

def animal_species(config):
    targets=config.get('classes',[])
    if 'Wildlife' not in targets and 'Living Organisms' not in targets:return []
    if 'organismCategories' in config:return LAND_MAMMALS.copy() if 'Land Mammals' in organism_categories(config) else []
    selected=config.get('wildlifeSpecies',list(ANIMAL_CLASS_IDS))
    if not isinstance(selected,list) or (not selected and 'Wildlife' in targets) or any(s not in ANIMAL_CLASS_IDS for s in selected):raise ValueError('Choose at least one supported animal class.')
    return list(dict.fromkeys(selected))

def needs_person_detector(config):
    return 'Humans' in organism_categories(config) if 'organismCategories' in config else 'Living Organisms' in config.get('classes',[])

def needs_overhead_locator(config):
    return 'organismCategories' in config and config.get('useAerialWildlife',True) and bool(set(organism_categories(config))&{'Land Mammals','Unclassified Wildlife'})

def animal_resolution_context(info):
    spacing=info['groundResolutionMeters']
    return {'experimental':True,'trainingDomain':'General COCO photographs plus OWL-C aerial localization when enabled; satellite accuracy not validated','samplingMetersPerPixel':spacing,'exampleFourMeterAnimalPixels':round(4/spacing,1) if spacing>0 else None,'nativeResolutionKnown':False,'note':'Sampling is not native source resolution. Small targets and canopy cover can prevent identification. No detections does not establish absence of animals.'}
