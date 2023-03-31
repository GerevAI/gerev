import * as React from "react";
import Select, {components} from 'react-select';
import copy from 'copy-to-clipboard';
import {confirmAlert} from 'react-confirm-alert'; // Import
import 'react-confirm-alert/src/react-confirm-alert.css'; // Import css
import CopyThis from '../assets/images/copy-this.png';
import LeftPane from '../assets/images/left-pane-instructions.png';

import {FaRegEdit} from "react-icons/fa";
import {AiFillCheckCircle} from "react-icons/ai";
import {BiLinkExternal} from 'react-icons/bi';
import {IoMdClose, IoMdCloseCircle} from "react-icons/io";
import {IoAddCircleOutline} from "react-icons/io5";
import {RxCopy} from 'react-icons/rx';
import {ClipLoader} from "react-spinners";
import {toast} from 'react-toastify';
import {api} from "../api";
import {ConfigField, ConnectedDataSource, DataSourceType, IndexLocation} from "../data-source";
import {useState} from "react";


export interface SelectOption {
    value: string;
    label: string;
    imageBase64: string
    configFields: ConfigField[]
    hasAdditionalSteps: boolean
}

export interface DataSourcePanelState {
    selectOptions: SelectOption[]
    isAdding: boolean
    selectedDataSource: SelectOption
    isLoading: boolean
    locations: IndexLocation[]
    selectedLocations: IndexLocation[]
    isSelectingLocations: boolean
    removeInProgressIndex: number
    editMode: boolean
}

export interface DataSourcePanelProps {
    dataSourceTypesDict: { [key: string]: DataSourceType }
    connectedDataSources: ConnectedDataSource[]
    inIndexing: boolean
    onAdded: (newlyConnected: ConnectedDataSource) => void
    onRemoved: (removed: ConnectedDataSource) => void
    onClose: () => void
}

const Option = props => (
    <components.Option {...props}>
        <div className="flex flex-row w-full">
            <img alt="logo" className={"mr-2 h-[20px]"} src={props.data.imageBase64}></img>
            {props.label}
        </div>
    </components.Option>
);


const slackManifest = {
    "display_information": {
        "name": "GerevAI"
    },
    "features": {
        "bot_user": {
            "display_name": "GerevAIBot"
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "channels:history",
                "channels:join",
                "channels:read",
                "users:read"
            ]
        }
    }
}

const capitilize = (str: string) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

const InputField = ({label, placeholder, onChange}: any) => {
    let [value, setValue] = useState('')
    return (
        <div className="flex flex-col mr-10 mt-4">
            <h1 className="text-lg block text-white mb-4">{label}</h1>
            <input value={value} onChange={(event) => {
                setValue(event.target.value)
                onChange(event.target.value)
            }}
                   className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2"
                   placeholder={placeholder}></input>
        </div>
    );
}
const TextAreaField = ({label, placeholder, onChange}: any) => {
     let [value, setValue] = useState('')
    return (
        <div className="flex flex-col w-full mt-4">
            <h1 className="text-lg block text-white mb-4">{label}</h1>
            <textarea value={value} onChange={(event) => {
                setValue(event.target.value)
                onChange(event.target.value)
            }}
                      className="w-full h-80 rounded-lg bg-[#352C45] text-white p-2 mb-5"
                      placeholder={placeholder}></textarea>
        </div>
    )
}

const DataSourcePanel = (props: DataSourcePanelProps) => {
    let options = Object.keys(props.dataSourceTypesDict).map((key) => {
        const { name, display_name, image_base64, config_fields, has_prerequisites } = props.dataSourceTypesDict[key];
        return {
            value: name,
            label: display_name,
            imageBase64: image_base64,
            configFields: config_fields,
            hasAdditionalSteps: has_prerequisites,
        };
    });
    let [state, setState] = React.useState<DataSourcePanelState>({
        selectOptions: options,
        selectedDataSource: options[0] || {
            value: 'unknown',
            label: 'unknown',
            imageBase64: '',
            configFields: [],
            hasAdditionalSteps: false
        },
        isAdding: false,
        isLoading: false,
        isSelectingLocations: false,
        locations: [],
        selectedLocations: [],
        removeInProgressIndex: -1,
        editMode: false
    })

    const dataSourceToAddSelected = (dataSource: DataSourceType) => {
        let selectedDataSource = state.selectOptions.find((option) => {
            return option.value === dataSource.name
        })

        if (!selectedDataSource) { // shouldn't happen, typescript...
            return;
        }

        setState({...state, isAdding: true, selectedDataSource: selectedDataSource})
    }

    const confirmDelete = (index: number) => {
        confirmAlert({
            title: 'Alert',
            message: `Are you sure you want to delete ${capitilize(props.connectedDataSources[index].name)}?`,
            buttons: [
                {
                    label: 'Yes, delete it',
                    onClick: () => removeDataSource(index)
                },
                {
                    label: 'No'
                }
            ]
        });
    };
    const proceed = () => {
        if (!state.selectedDataSource.hasAdditionalSteps) {
            return submit();
        }

        if (!state.isSelectingLocations) {
            return getLocations();
        }

        if (state.selectedLocations.length === 0) {
            toast.error("Please select at least one location to index");
            return;
        }

        submit();
    }

    const copyManifest = () => {
        let manifestText = JSON.stringify(slackManifest);
        if (!copy(manifestText)) {
            toast.error("Error copying manifest");
        } else {
            toast.success("Manifest copied to clipboard", {autoClose: 2000});
        }
    }

    const getLocations = async () => {
        if (!state.selectedDataSource) return;

        let config = {};
        state.selectedDataSource.configFields.forEach(field => {
            config[field.name] = field.value;
        });

        toast.info("Looking for confluence spaces (this may take a while)", {autoClose: 6000});

        setState({...state, isLoading: true});
        try {
            let response = await api.post<IndexLocation[]>(`/data-sources/${state.selectedDataSource.value}/list-locations`,
                config, {
                    headers: {
                        uuid: localStorage.getItem('uuid')
                    }
                })
            toast.dismiss();
            toast.success("Listed locations", {autoClose: 2000});
            setState({...state, isSelectingLocations: true, locations: response.data, isLoading: false});
        } catch (error) {
            toast.dismiss();
            toast.error("Error listing locations: " + error.response.data, {autoClose: 10000});
            setState({...state, isLoading: false});

        }
    }

    const indexEverything = () => {
        setState({...state, selectedLocations: []});
        submit();
    }

    const submit = async () => {
        if (!state.selectedDataSource || state.isLoading) return;

        let config = {};
        state.selectedDataSource.configFields.forEach(field => {
            config[field.name] = field.value;
        });
        config['locations_to_index'] = state.selectedLocations;

        let payload = {
            name: state.selectedDataSource.value,
            config: config
        }
        setState({...state, isLoading: true});
        try {
            let response = await api.post(`/data-sources`, payload, {
                headers: {
                    uuid: localStorage.getItem('uuid')
                }
            })
            toast.success("Data source added successfully, indexing...");
            let selectedDataSource = state.selectedDataSource;
            selectedDataSource.configFields.forEach(field => {
                field.value = '';
            });
            setState({...state, selectedDataSource: selectedDataSource});
            props.onAdded({name: state.selectedDataSource.value, id: response.data});
            reset();
        } catch (error) {
            toast.error("Error adding data source: " + error.response.data, {autoClose: 10000});
            setState({...state, isLoading: false});
        }
    }

    const reset = () => {
        setState({
            ...state,
            isLoading: false,
            isAdding: false,
            selectedDataSource: state.selectOptions[0],
            isSelectingLocations: false,
            selectedLocations: []
        });
    }
    const onLocationsSelectChange = (event) => {
        setState({...state, selectedLocations: event});
    }

    const onSourceSelectChange = (event) => {
        setState({...state, selectedDataSource: event, isSelectingLocations: false, selectedLocations: []});
    }

    const removeDataSource = async (index: number) => {
        if (props.inIndexing) {
            toast.error("Cannot remove data source while indexing is in progress");
            return;
        }

        if (state.removeInProgressIndex !== -1) {
            toast.error("Cannot remove data source while another is being removed");
            return;
        }

        let connectedDataSource = props.connectedDataSources[index];
        setState({...state, removeInProgressIndex: index});
        try {
            await api.delete(`/data-sources/${connectedDataSource.id}`, {
                headers: {
                    uuid: localStorage.getItem('uuid')
                }
            })
            toast.success(`${capitilize(connectedDataSource.name)} removed.`);
            setState({...state, removeInProgressIndex: -1});
            props.onRemoved(connectedDataSource);
        } catch (error) {
            toast.error("Error removing data source: " + error.response.data, {autoClose: 10000});

        }
    }

    const switchMode = () => {
        setState({...state, editMode: !state.editMode})
    }
    return (
        <div className="relative flex flex-col bg-[#221f2e] items-start px-8 pt-0 pb-4 min-h-[300px]">
            {
                !state.isAdding &&
                <h1 className="mt-4 relative self-center text-white block text-4xl mb-8 font-poppins">Data Source
                    Panel</h1>
            }

            {/* X and Edit in top right */}
            <div className="absolute flex flex-col items-center right-4 top-3 text-2xl text-white gap-4">
                <IoMdClose onClick={props.onClose} className='hover:text-[#9875d4] hover:cursor-pointer'/>

            </div>

            {/* Panel main page */}
            {
                !state.isAdding && (
                    <div className="w-full">
                        <h1 className="text-2xl block text-white mb-4">
                            {props.connectedDataSources.length > 0 ? (state.editMode ? 'Edit mode:' : 'Active data sources:') : 'No Active Data Sources. Add Now!'}
                            {props.connectedDataSources.length > 0 && <FaRegEdit key="pencil" onClick={switchMode}
                                                                                 className='text-white mt-1 float-right inline hover:text-[#9875d4] hover:cursor-pointer'/>}
                        </h1>
                        <div className="flex flex-row w-[100%] flex-wrap">
                            {props.connectedDataSources.map((dataSource, index) => {
                                return (
                                    // connected data source
                                    <div
                                        key={index}
                                        className="flex py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#352C45] hover:shadow-inner shadow-blue-500/50 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
                                        <img alt="data-source" className={"mr-2 h-[20px]"}
                                             src={props.dataSourceTypesDict[dataSource.name].image_base64}></img>
                                        <h1 className="text-white width-full">{props.dataSourceTypesDict[dataSource.name].display_name}</h1>

                                        {state.editMode ? (
                                                state.removeInProgressIndex === index ?
                                                    (
                                                        <ClipLoader className="ml-3" color="#7d4ac3" loading={true} size={16}
                                                                    aria-label="Removing..."/>
                                                    ) :
                                                    (
                                                        <IoMdCloseCircle onClick={() => confirmDelete(index)}
                                                                         className="transition duration-150 ease-in-out  ml-6 fill-[#7d4ac3] hover:cursor-pointer text-2xl hover:fill-[#d80b0b]"/>
                                                    )
                                            )
                                            :
                                            (
                                                <AiFillCheckCircle className="ml-6 text-[#9875d4] text-2xl"/>
                                            )
                                        }

                                    </div>
                                )
                            })
                            }
                            {
                                Object.keys(props.dataSourceTypesDict).map((key, index) => {
                                    let dataSource = props.dataSourceTypesDict[key];
                                    if (!state.editMode && !props.connectedDataSources.find((connectedDataSource) => connectedDataSource.name === dataSource.name)) {
                                        return (
                                            // unconnected data source
                                            <div index={index} onClick={() => dataSourceToAddSelected(dataSource)}
                                                 className="flex hover:text-[#9875d4] py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#36323b] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#777777] border-b-[.5px] transition duration-300 ease-in-out">
                                                <img alt="" className={"mr-2 h-[20px]"} src={dataSource.image_base64}></img>
                                                {/* <h1 className="text-white">Add</h1> */}
                                                <h1 className="text-gray-500">{dataSource.display_name}</h1>
                                                <IoAddCircleOutline
                                                    className="ml-6 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                                            </div>
                                        )
                                    }
                                    return null;

                                })
                            }
                            <div onClick={() => setState({...state, isAdding: true})}
                                 className="flex hover:text-[#9875d4] py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#36323b] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#777777] border-b-[.5px] transition duration-300 ease-in-out">
                                <h1 className="text-gray-500">Add</h1>
                                <IoAddCircleOutline
                                    className="ml-4 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* instructions + input page */}

            {
                state.isAdding && (
                    <div className="flex flex-col w-[100%] py-10">
                        <div className="flex flex-row justify-left ml-2 items-center mb-5 mt-5">
                            <img alt="" className={"mr-2 h-[32px]"} src={state.selectedDataSource.imageBase64}></img>
                            <Select className="w-60 text-white" onChange={onSourceSelectChange}
                                    value={state.selectedDataSource}
                                    options={state.selectOptions} isDisabled={false} isSearchable={false}
                                    components={{Option}}
                                    styles={{
                                        control: (baseStyles, state) => ({
                                            ...baseStyles,
                                            backgroundColor: '#352c45',
                                            borderColor: '#472f61'
                                        }),
                                        singleValue: (baseStyles, state) => ({
                                            ...baseStyles,
                                            color: '#ffffff',
                                        }),
                                        option: (baseStyles, state) => ({
                                            ...baseStyles,
                                            backgroundColor: '#352c45',
                                            ':hover': {
                                                backgroundColor: '#52446b',
                                            },
                                        }),
                                        valueContainer: (baseStyles, state) => ({
                                            ...baseStyles,
                                            backgroundColor: '#352c45',
                                        }),
                                        menuList: (baseStyles, state) => ({
                                            ...baseStyles,
                                            backgroundColor: '#352c45',
                                        }),
                                    }}/>
                        </div>
                        {
                            // instructions
                            <div className="flex flex-col ">
                                <div className="bg-[#352C45] py-[26px] px-10 rounded-xl border-[1px] border-[#4e326b]">
                                    {
                                        state.selectedDataSource.value === 'mattermost' && (
                                            <span className="flex flex-col leading-9  text-xl text-white">
                                       <span>1. {'Go to your Mattermost -> top-right profile picture -> Profile'}</span>
                                       <span>2. {'Security -> Personal Access Tokens -> Create token -> Name it'}</span>
                                       <span>3. {"Copy the Access Token"}</span>
                                       <span
                                           className="text-violet-300/[.75] text-sm"> {"* Personal Access Tokens must be on"} - <a
                                           className="inline hover:underline text-violet-400/[.75]" target="_blank"
                                           rel="noreferrer"
                                           href="https://developers.mattermost.com/integrate/reference/personal-access-token/">Click for more info</a></span>
                                    </span>
                                        )
                                    }
                                    {
                                        state.selectedDataSource.value === 'confluence' && (
                                            <span className="flex flex-col leading-9  text-xl text-white">
                                       <span>1. {'Go to your Confluence -> top-right profile picture -> Settings'}</span>
                                       <span>2. {'Personal Access Tokens -> Create token -> Name it'}</span>
                                       <span>3. {"Uncheck 'Automatic expiry', create and copy the token"}</span>
                                    </span>
                                        )
                                    }
                                    {
                                        state.selectedDataSource.value === 'confluence_cloud' && (
                                            <span className="flex flex-col leading-9  text-xl text-white">
                                       <span>1. {'Go to your Confluence -> top-right profile picture -> Manage account'}</span>
                                       <span>2. {'go security tab (at top) -> Create and manage API tokens -> Create API token'}</span>
                                       <span>3. {"Name it, create and copy the token"}</span>
                                    </span>
                                        )
                                    }
                                    {state.selectedDataSource.value === 'slack' && (
                                        // slack instructions
                                        <span className=" flex flex-col leading-9 text-lg text-white">
                                    <span className="flex flex-row items-center">1.
                                       <button onClick={copyManifest}
                                               className="flex py-3 pl-3 pr-2 m-2 w-[110px] h-10 text-lg flex-row items-center justify-center bg-[#584971] active:transform active:translate-y-4 hover:bg-[#9875d4] rounded-lg font-poppins border-[#ffffff] border-b-[.5px] transition duration-300 ease-in-out">
                                          <span>Copy</span>
                                          <RxCopy className="ml-2"></RxCopy>
                                       </button>
                                       <span>our JSON app manifest.</span>
                                    </span>
                                    <span className="flex flex-row items-center"> 2. Create new app
                                       from manifest in &nbsp;
                                        <a className="text-[#d6acff] hover:underline" rel="noreferrer"
                                           href={'https://api.slack.com/apps'} target='_blank'>
                                          Slack Apps
                                       </a>
                                        &nbsp; <BiLinkExternal color="#d6acff"></BiLinkExternal>
                                    </span>
                                    <span className="ml-8 flex flex-row items-center my-3">
                                       <span
                                           className="bg-[#007a5a] pb-[9px] pt-2 px-[14px] text-[15px] w-[146px] h-9 rounded font-[800] text-center leading-5">
                                          Create new App
                                       </span>
                                       <span className="mx-3">{' ->'}</span>
                                       <span
                                           className="flex flex-row items-center leading-6 font-medium rounded bg-white py-[5px] px-3">
                                          <span className="text-[15px] text-black">From an app manifest</span>
                                          <span
                                              className="ml-[10px] text-[#1264a3] bg-[#e8f5fa] shadow-[inset_0_0_0_1px_#1d9bd11a]  leading-3 text-[10px] p-1 font-bold">
                                             BETA
                                          </span>
                                       </span>

                                    </span>
                                    <span>3. {"Install App to Workspace."}</span>
                                    <span className="ml-8 flex flex-row items-center my-3">
                                       <span
                                           className="bg-[#fff] text-[#1d1c1d] border-[#1D1C1D] border-[1px] pb-[9px] pt-2 px-[14px] text-[15px] w-44 h-9 rounded font-semibold text-center leading-5">
                                          Install to Workspace
                                       </span>
                                    </span>
                                    <span>4. Click left panel OAuth & Permissions.</span>
                                    <span className="ml-8 mt-2">
                                       <img alt="" className="h-[120px] rounded-xl p-1" src={LeftPane}/>
                                    </span>
                                    <span>5. Copy the Bot User OAuth Token.</span>
                                    <span className="ml-8 mt-2">
                                       <img alt="" className="h-[120px] rounded-xl p-1" src={CopyThis}/>
                                    </span>
                                    <span className="text-violet-300/[.75] mt-1 text-sm"> *Gerev bot will join your channels.</span>
                                 </span>
                                    )
                                    }
                                    {state.selectedDataSource.value === 'google_drive' && (
                                        // Google Drive instructions
                                        <span className="leading-9 text-lg text-white">
                                    Follow <a
                                            href='https://github.com/GerevAI/gerev/blob/main/docs/data-sources/google-drive/google-drive.md'
                                            rel="noreferrer" className="inline underline"
                                            target="_blank">these instructions</a>
                                 </span>
                                    )}
                                    {
                                        state.selectedDataSource.value === 'bookstack' && (
                                            <span className="flex flex-col leading-9  text-xl text-white">
                                       <span>1. {'Go to your Bookstack -> top-right profile picture -> Edit profile'}</span>
                                       <span>2. {'Scroll down to API tokens -> Create token -> Name it'}</span>
                                       <span>3. {"Set 'Expiry Date' 01/01/2100, create, copy token id + token secret"}</span>
                                    </span>
                                        )
                                    }
                                    {state.selectedDataSource.value === 'rocketchat' && (
                                        <span className="flex flex-col leading-9  text-xl text-white">
                                    <span>1. {'In Rocket.Chat, click your profile picture -> My Account.'}</span>
                                    <span>2. {'Click Personal Access Tokens.'}</span>
                                    <span>3. {'Check "Ignore Two Factor Authentication".'}</span>
                                    <span>4. {'Give the token a name and press "Add".'}</span>
                                    <span>5. {'Type in your password, if needed.'}</span>
                                    <span>6. {'Copy the token and user id here.'}</span>
                                    <p>Note that the url must begin with either http:// or https://</p>
                                 </span>
                                    )}
                                    {state.selectedDataSource.value === 'stack_overflow' && (
                                        <span className="flex flex-col leading-9  text-xl text-white">
                                    <span>1. {'Visit: https://stackoverflowteams.com/users/pats/'}</span>
                                    <span>2. {'Click Create a new PAT'}</span>
                                    <span>3. {'Name the token, and pick the team scope.'}</span>
                                    <span>4. {'Select an expiration date'}</span>
                                    <span>5. {'Click Create'}</span>
                                 </span>
                                    )}
                                </div>

                                <div className="flex flex-row flex-wrap items-end mt-4">
                                    {/* for each field */}
                                    {
                                        state.selectedDataSource.configFields.map((field, index) => {
                                            if (field.input_type === 'text' || field.input_type === 'password') {
                                                return (<InputField key={index} {...field} onChange={(value) => {
                                                    state.selectedDataSource.configFields[index].value = value;
                                                    setState({...state});
                                                }} />)
                                            } else if (field.input_type === 'textarea') {
                                                return (<TextAreaField key={index} {...field} onChange={(value) => {
                                                    state.selectedDataSource.configFields[index].value = value;
                                                    setState({...state});
                                                }} />)
                                            }
                                            return null;
                                        })
                                    }
                                    {/* Selecting locations */}
                                    {
                                        state.isSelectingLocations && (
                                            <div className="flex flex-col w-[100%]">
                                                <div className="flex flex-row justify-left ml-2 items-center mb-5 mt-5">
                                                    <div className="flex flex-col mr-10 mt-4">
                                                        <h1 className="text-lg block text-white mb-4">Select locations to
                                                            index</h1>
                                                        <Select className="w-[500px] text-white" isMulti
                                                                onChange={onLocationsSelectChange}
                                                                options={state.locations} isDisabled={false} isSearchable={true}
                                                                value={state.selectedLocations}
                                                                styles={{
                                                                    control: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        backgroundColor: '#352c45',
                                                                        borderColor: '#472f61'
                                                                    }),
                                                                    singleValue: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        color: '#ffffff',
                                                                    }),
                                                                    option: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        backgroundColor: '#352c45',
                                                                        ':hover': {
                                                                            backgroundColor: '#52446b',
                                                                        },
                                                                    }),
                                                                    valueContainer: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        backgroundColor: '#352c45',
                                                                        color: '#ffffff',
                                                                    }),
                                                                    menuList: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        backgroundColor: '#352c45',
                                                                    }),
                                                                    input: (baseStyles, state) => ({
                                                                        ...baseStyles,
                                                                        color: '#ffffff',
                                                                    })
                                                                }}/>
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    }
                                    <div onClick={proceed} className="flex py-2 px-3 mx-2 w-30 h-10 mt-4 flex-row items-center justify-center bg-[#352C45]
                                  hover:bg-[#7459a1] hover:cursor-pointer rounded-lg font-poppins leading-[28px] border-[#522b60] transition duration-300 ease-in-out">
                                        {!state.isLoading && !state.selectedDataSource.hasAdditionalSteps &&
                                            <h1 className="text-white">Submit</h1>}

                                        {!state.isLoading && state.selectedDataSource.hasAdditionalSteps &&
                                            <h1 className="text-white">
                                                {state.isSelectingLocations ? `Proceed with ${state.selectedLocations.length} locatons` :
                                                    'Proceed'}
                                            </h1>}

                                        {
                                            state.isLoading &&
                                            <ClipLoader
                                                color="#ffffff"
                                                loading={true}
                                                size={25}
                                                aria-label="Loading Spinner"
                                            />
                                        }
                                    </div>
                                    {
                                        state.isSelectingLocations && (
                                            <div onClick={indexEverything} className="flex py-2 px-3 mx-2 w-30 h-10 mt-4 flex-row items-center justify-center bg-[#352C45]
                                  hover:bg-[#7459a1] hover:cursor-pointer rounded-lg font-poppins leading-[28px] border-[#522b60] transition duration-300 ease-in-out">
                                                <h1 className="text-white">or Index everything</h1>

                                                {
                                                    state.isLoading &&
                                                    <ClipLoader
                                                        color="#ffffff"
                                                        loading={true}
                                                        size={25}
                                                        aria-label="Loading Spinner"
                                                    />
                                                }
                                            </div>
                                        )}
                                </div>
                            </div>
                        }
                    </div>
                )
            }
        </div>
    );
}

export default DataSourcePanel;