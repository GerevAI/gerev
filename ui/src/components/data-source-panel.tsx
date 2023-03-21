import * as React from "react";
import Select, { components } from 'react-select';
import copy from 'copy-to-clipboard';

import CopyThis from '../assets/images/copy-this.png';
import LeftPane from '../assets/images/left-pane-instructions.png';

import { AiFillCheckCircle } from "react-icons/ai";
import { BiLinkExternal } from 'react-icons/bi';
import { IoMdClose } from "react-icons/io";
import { IoAddCircleOutline } from "react-icons/io5";
import { RxCopy } from 'react-icons/rx';
import { ClipLoader } from "react-spinners";
import { toast } from 'react-toastify';
import { api } from "../api";
import { ConfigField, DataSourceType } from "../data-source";


export interface SelectOption {
   value: string;
   label: string;
   imageBase64: string
   configFields: ConfigField[]
}

export interface ConfluenceConfig {
   url: string;
   token: string;
}

export interface SlackConfig {
   token: string;
}

export interface DataSourcePanelState {
   selectOptions: SelectOption[]
   isAdding: boolean
   selectedDataSource: SelectOption
   isAddingLoading: boolean
}

export interface DataSourcePanelProps {
   dataSourceTypesDict: { [key: string]: DataSourceType }
   connectedDataSources: string[]
   onAdded: (dataSourceType: string) => void
   onClose: () => void
}

const Option = props => (
   <components.Option {...props}>
      <div className="flex flex-row w-full">
         <img alt="logo" className={"mr-2 h-[20px]"} src={props.image_base64}></img>
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

export default class DataSourcePanel extends React.Component<DataSourcePanelProps, DataSourcePanelState> {

   constructor(props) {
      super(props);
      this.state = {
         selectOptions: [],
         isAdding: false,
         isAddingLoading: false,
         selectedDataSource: { value: 'unknown', label: 'unknown', imageBase64: '', configFields: []}
      }
   }

   async componentDidMount() {
      let options = Object.keys(this.props.dataSourceTypesDict).map((key) => {
         let data_source = this.props.dataSourceTypesDict[key];
         return {
            value: data_source.name,
            label: data_source.display_name,
            imageBase64: data_source.image_base64,
            configFields: data_source.config_fields
         }}
      );
      
      this.setState({
         selectOptions: options,
         selectedDataSource: options[0],
      })
   }

   capitilize(str: string) {
      return str.charAt(0).toUpperCase() + str.slice(1);
   }

   dataSourceToAddSelected(dataSource: DataSourceType) {
      let selectedDataSource = this.state.selectOptions.find((option) => {
         return option.value === dataSource.name
      })

      if (!selectedDataSource) { // shoudln't happen, typescript...
         return;
      }

      this.setState({ isAdding: true, selectedDataSource: selectedDataSource })
   }


   render() {
      return (
         <div className="relative flex flex-col bg-[#221f2e] items-start px-8 pt-0 pb-4 min-h-[300px]">
            {
               !this.state.isAdding && <h1 className="mt-4 relative self-center text-white block text-4xl mb-8 font-poppins">Data Source Panel</h1>
            }
            <IoMdClose onClick={this.props.onClose} className='absolute right-4 top-3 text-2xl text-white hover:text-[#9875d4] hover:cursor-pointer'></IoMdClose>
            {
               !this.state.isAdding && (
                  <div>
                     <h1 className="text-2xl block text-white mb-4">
                        {this.props.connectedDataSources.length > 0 ? 'Active data sources:' : 'No Active Data Sources. Add Now!'}
                     </h1>
                     <div className="flex flex-row w-[100%] flex-wrap">
                        {this.props.connectedDataSources.map((data_source) => {
                           return (
                              <div className="flex py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#352C45] hover:shadow-inner shadow-blue-500/50 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
                                 <img alt="data-source" className={"mr-2 h-[20px]"} src={this.props.dataSourceTypesDict[data_source].image_base64}></img>
                                 <h1 className="text-white">{this.props.dataSourceTypesDict[data_source].display_name}</h1>
                                 <AiFillCheckCircle className="ml-6 text-[#9875d4] text-2xl"> </AiFillCheckCircle>
                              </div>
                           )
                        })
                        }
                        {
                        Object.keys(this.props.dataSourceTypesDict).map((key) => {
                           let dataSource = this.props.dataSourceTypesDict[key];
                           if (!this.props.connectedDataSources.includes(dataSource.name)) {
                              return (
                                 <div onClick={() => this.dataSourceToAddSelected(dataSource)} className="flex hover:text-[#9875d4] py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#36323b] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#777777] border-b-[.5px] transition duration-300 ease-in-out">
                                    <img alt="" className={"mr-2 h-[20px]"} src={dataSource.image_base64}></img>
                                    {/* <h1 className="text-white">Add</h1> */}
                                    <h1 className="text-gray-500">{dataSource.display_name}</h1>
                                    <IoAddCircleOutline className="ml-6 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                                 </div>
                              )
                           }
                           return null;

                        })
                        }
                     </div>
                  </div>)
            }
            {
               this.state.isAdding && (
                  <div className="flex flex-col w-[100%]">
                     <div className="flex flex-row justify-left ml-2 items-center mb-5 mt-5">
                        <img alt="" className={"mr-2 h-[32px]"} src={this.state.selectedDataSource.imageBase64}></img>
                        <Select className="w-40 text-white" onChange={this.onSelectChange} value={this.state.selectedDataSource}
                           options={this.state.selectOptions} isDisabled={false} isSearchable={false} components={{ Option }}
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
                           }} />
                     </div>
                     {
                        <div className="flex flex-col ">
                           <div className="bg-[#352C45] py-[26px] px-10 rounded-xl border-[1px] border-[#4e326b]">
                              {
                                 this.state.selectedDataSource.value === 'confluence' && (
                                    <span className="flex flex-col leading-9  text-xl text-white">
                                       <span>1. {'Go to your Confluene -> top-right profile picture -> Settings'}</span>
                                       <span>2. {'Personal Access Tokens -> Create token -> Name it'}</span>
                                       <span>3. {"Uncheck 'Automatic expiry', create and copy the token"}</span>
                                    </span>
                                 )
                              }
                              {this.state.selectedDataSource.value === 'slack' && (
                                 <span className=" flex flex-col leading-9 text-lg text-white">
                                    <span className="flex flex-row items-center">1.
                                       <button onClick={this.copyManifest} className="flex py-3 pl-3 pr-2 m-2 w-[110px] h-10 text-lg flex-row items-center justify-center bg-[#584971] active:transform active:translate-y-4 hover:bg-[#9875d4] rounded-lg font-poppins border-[#ffffff] border-b-[.5px] transition duration-300 ease-in-out">
                                          <span>Copy</span>
                                          <RxCopy className="ml-2"></RxCopy>
                                       </button>
                                       <span>our JSON app manifest.</span>
                                    </span>
                                    <span className="flex flex-row items-center"> 2. Create new app
                                       from manifest in &nbsp;
                                       <a className="text-[#d6acff] hover:underline" rel="noreferrer" href={'https://api.slack.com/apps'} target='_blank'>
                                          Slack Apps
                                       </a>
                                       &nbsp; <BiLinkExternal color="#d6acff"></BiLinkExternal>
                                    </span>
                                    <span className="ml-8 flex flex-row items-center my-3">
                                       <span className="bg-[#007a5a] pb-[9px] pt-2 px-[14px] text-[15px] w-[146px] h-9 rounded font-[800] text-center leading-5">
                                          Create new App
                                       </span>
                                       <span className="mx-3">{' ->'}</span>
                                       <span className="flex flex-row items-center leading-6 font-medium rounded bg-white py-[5px] px-3">
                                          <span className="text-[15px] text-black">From an app manifest</span>
                                          <span className="ml-[10px] text-[#1264a3] bg-[#e8f5fa] shadow-[inset_0_0_0_1px_#1d9bd11a]  leading-3 text-[10px] p-1 font-bold">
                                             BETA
                                          </span>
                                       </span>

                                    </span>
                                    <span>3. {"Install App to Workspace."}</span>
                                    <span className="ml-8 flex flex-row items-center my-3">
                                       <span className="bg-[#fff] text-[#1d1c1d] border-[#1D1C1D] border-[1px] pb-[9px] pt-2 px-[14px] text-[15px] w-44 h-9 rounded font-semibold text-center leading-5">
                                          Install to Workspace
                                       </span>
                                    </span>
                                    <span>4. Click left panel OAuth & Permissions.</span>
                                    <span className="ml-8 mt-2">
                                       <img alt="" className="h-[120px] rounded-xl p-1" src={LeftPane} />
                                    </span>
                                    <span>5. Copy the Bot User OAuth Token.</span>
                                    <span className="ml-8 mt-2">
                                       <img alt="" className="h-[120px] rounded-xl p-1" src={CopyThis} />
                                    </span>
                                 </span>
                              )
                              }

                              {this.state.selectedDataSource.value === 'google_drive' && (
                                 <span className="leading-9 text-lg text-white">
                                    Follow <a href='https://github.com/GerevAI/gerev/blob/main/docs/data-sources/google-drive/google-drive.md' rel="noreferrer" className="inline underline" target="_blank">these instructions</a>
                                 </span>
                              )}
                           </div>

                           <div className="flex flex-row flex-wrap items-end mt-4">
                              {/* for each field */}
                              {
                              this.state.selectedDataSource.configFields.map((field, index) => {
                                 if(field.input_type === 'text' || field.input_type === 'password') {
                                    return (
                                       <div className="flex flex-col mr-10">
                                          <h1 className="text-lg block text-white mb-4">{field.label}</h1>
                                          <input value={field.value} onChange={(event) => {field.value = event.target.value }}
                                          className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2"
                                           placeholder={field.placeholder}></input>
                                       </div>
                                    )
                                 } else if (field.input_type === 'textarea') {
                                    return (
                                       <div className="flex flex-col w-full">
                                        <h1 className="text-lg block text-white mb-4">{field.label}</h1>
                                          <textarea value={field.value} onChange={(event) => {field.value = event.target.value }}
                                            className="w-full h-80 rounded-lg bg-[#352C45] text-white p-2 mb-5" placeholder={field.placeholder}></textarea>
                                     </div>
                                    )}
                                    return null;
                              })
                              }
                              <div onClick={this.submit} className="flex py-2 px-3 mx-2 w-30 h-10 mt-4 flex-row items-center justify-center bg-[#352C45]
                                  hover:bg-[#7459a1] hover:cursor-pointer rounded-lg font-poppins leading-[28px] border-[#522b60] transition duration-300 ease-in-out">
                                 {!this.state.isAddingLoading && <h1 className="text-white">Submit</h1>}
                                 {
                                    this.state.isAddingLoading &&
                                    <ClipLoader
                                       color="#ffffff"
                                       loading={true}
                                       size={25}
                                       aria-label="Loading Spinner"
                                    />
                                 }
                              </div>
                           </div>
                        </div>
                     }
                  </div>
               )}
         </div>
      );
   }

   copyManifest = () => {
      let manifestText = JSON.stringify(slackManifest);
      if(!copy(manifestText)) {
         toast.error("Error copying manifest");
      } else {
         toast.success("Manifest copied to clipboard", { autoClose: 2000 });
      }
   }


   submit = () => {
      if (!this.state.selectedDataSource) return;

      let config = {};
      this.state.selectedDataSource.configFields.forEach(field => {
         config[field.name] = field.value;
      });
      
      let payload = {
         name: this.state.selectedDataSource.value,
         config: config
      }
      this.setState({ isAddingLoading: true });
      api.post(`/data-source/add`, payload).then(response => {
         toast.success("Data source added successfully, indexing...");
         this.props.onAdded(this.state.selectedDataSource.value);
         this.setState({isAddingLoading: false, isAdding: false, selectedDataSource: this.state.selectOptions[0]});
      }).catch(error => {
         toast.error("Error adding data source: " + error.response.data, { autoClose: 10000 });
         this.setState({ isAddingLoading: false });
      });
   }

   onSelectChange = (event) => {
      this.setState({ selectedDataSource: event })
   }
}