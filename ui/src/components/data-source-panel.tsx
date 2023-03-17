import * as React from "react";
import Select, { components } from 'react-select';
import { Platform, getPlatformDisplayName } from "./search-result";

import Confluence from '../assets/images/confluence.svg';
import CopyThis from '../assets/images/copy-this.png';
import LeftPane from '../assets/images/left-pane-instructions.png';
import Slack from '../assets/images/slack.svg';
import GoogleDrive from '../assets/images/google-drive.svg'


import { AiFillCheckCircle } from "react-icons/ai";
import { BiLinkExternal } from 'react-icons/bi';
import { IoMdClose } from "react-icons/io";
import { IoAddCircleOutline } from "react-icons/io5";
import { RxCopy } from 'react-icons/rx';
import { ClipLoader } from "react-spinners";
import { toast } from 'react-toastify';
import { api } from "../api";


export interface SelectOption {
   value: string;
   label: string;
}

export interface ConfluenceConfig {
   url: string;
   token: string;
}

export interface SlackConfig {
   token: string;
}

export interface DataSourcePanelState {
   dataSourceTypes: SelectOption[]
   isAdding: boolean
   selectedDataSource: SelectOption
   isAddingLoading: boolean
   newUrl: string
   newToken: string
   newBigText: string
}

export interface DataSourcePanelProps {
   connectedDataSources: string[]
   onAdded: (dataSourceType: string) => void
   onClose: () => void
}

function getBigIconByPlatform(platform: Platform) {
   switch (platform) {
      case Platform.Confluence:
         return Confluence
      case Platform.Slack:
         return Slack;
      case Platform.Drive:
         return GoogleDrive;
   }
}

const Option = props => (
   <components.Option {...props}>
      <div className="flex flex-row w-full">
         <img className={"mr-2 h-[20px]"} src={getBigIconByPlatform(props.value)}></img>
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
         isAdding: false,
         isAddingLoading: false,
         selectedDataSource: { value: 'unknown', label: 'unknown' },
         dataSourceTypes: [
         ],
         newUrl: '',
         newToken: '',
         newBigText: ''
      }
   }

   async componentDidMount() {
      this.listAvailableDataSourceTypes();
   }

   async listAvailableDataSourceTypes() {
      try {
         const response = await api.get('/data-source/list-types');
         let types = this.dataSourceNamesToSelectOptions(response.data);
         this.setState({
            dataSourceTypes: types,
            selectedDataSource: types[1]
         })
      } catch (error) {
      }
   }

   dataSourceNamesToSelectOptions(dataSourceNames: string[]) {
      return dataSourceNames.map((data_source) => {
         return {
            value: data_source,
            label: getPlatformDisplayName(data_source as Platform)
         }
      })
   }

   capitilize(str: string) {
      return str.charAt(0).toUpperCase() + str.slice(1);
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
                                 <img className={"mr-2 h-[20px]"} src={getBigIconByPlatform(data_source as Platform)}></img>
                                 <h1 className="text-white">{getPlatformDisplayName(data_source as Platform)}</h1>
                                 <AiFillCheckCircle className="ml-6 text-[#9875d4] text-2xl"> </AiFillCheckCircle>
                              </div>
                           )
                        })
                        }
                        {
                        this.state.dataSourceTypes.map((data_source) => {
                           if (!this.props.connectedDataSources.includes(data_source.value)) {
                              return (
                                 <div onClick={() => { this.setState({ isAdding: true, selectedDataSource: data_source }) }} className="flex hover:text-[#9875d4] py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#36323b] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#777777] border-b-[.5px] transition duration-300 ease-in-out">
                                    <img className={"mr-2 h-[20px]"} src={getBigIconByPlatform(data_source.value as Platform)}></img>
                                    {/* <h1 className="text-white">Add</h1> */}
                                    <h1 className="text-gray-500">{getPlatformDisplayName(data_source.value as Platform)}</h1>
                                    <IoAddCircleOutline className="ml-6 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                                 </div>
                              )
                           }
                        })
                        }
                     </div>
                  </div>)
            }
            {
               this.state.isAdding && (
                  <div className="flex flex-col w-[100%]">
                     <div className="flex flex-row justify-left ml-2 items-center mb-5 mt-5">
                        <img className={"mr-2 h-[32px]"} src={getBigIconByPlatform(this.state.selectedDataSource.value as Platform)}></img>
                        <Select className="w-40 text-white" onChange={this.onSelectChange} value={this.state.selectedDataSource}
                           options={this.state.dataSourceTypes} isDisabled={false} isSearchable={false} components={{ Option }}
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
                                       <span>1. {'Go to your Confluene -\> top-right profile picture -\> Settings'}</span>
                                       <span>2. {'Personal Access Tokens -\> Create token -\> Name it'}</span>
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
                                       <a className="text-[#d6acff] hover:underline" href={'https://api.slack.com/apps'} target='_blank'>
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
                                       <img className="h-[120px] rounded-xl p-1" src={LeftPane} />
                                    </span>
                                    <span>5. Copy the Bot User OAuth Token.</span>
                                    <span className="ml-8 mt-2">
                                       <img className="h-[120px] rounded-xl p-1" src={CopyThis} />
                                    </span>
                                 </span>
                              )
                              }

                              {this.state.selectedDataSource.value === 'google_drive' && (
                                 <span className="leading-9 text-lg text-white">
                                    Follow <a href='https://github.com/GerevAI/gerev/blob/main/docs/data-sources/google-drive/google-drive.md' className="inline underline" target="_blank">these instructions</a>
                                 </span>
                              )}
                           </div>

                           <div className="flex flex-row flex-wrap items-end mt-4">
                              {
                                 this.hasUrl() &&
                                 <div className="flex flex-col mr-10">
                                    <h1 className="text-lg block text-white mb-4">{this.state.selectedDataSource.label} URL</h1>
                                    <input value={this.state.newUrl} onChange={(event) => this.setState({ newUrl: event.target.value })}
                                       className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2" placeholder="https://example.com"></input>
                                 </div>
                              }
                              {
                                 this.hasToken() &&
                                 <div className="flex flex-col">
                                    <h1 className="text-lg block text-white mb-4">
                                       {this.state.selectedDataSource.value == "slack" ? "Bot User OAuth Token" : "Personal Access Token"}
                                    </h1>
                                    <input value={this.state.newToken} onChange={(event) => this.setState({ newToken: event.target.value })}
                                       className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2" placeholder="paste-your-token-here"></input>
                                 </div>
                              }
                              {
                                 this.hasBigText() &&
                                 <div className="flex flex-col w-full">
                                    <h1 className="text-lg block text-white mb-4">JSON file content:</h1>
                                    <textarea value={this.state.newBigText} onChange={(event) => this.setState({ newBigText: event.target.value })}
                                       className="w-full h-80 rounded-lg bg-[#352C45] text-white p-2 mb-5" placeholder="Paste JSON here"></textarea>
                                 </div>
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
      navigator.clipboard.writeText(JSON.stringify(slackManifest));
   }

   hasUrl = () => {
      return this.state.selectedDataSource?.value === "confluence";
   }

   hasToken = () => {
      return this.state.selectedDataSource?.value === "confluence" || this.state.selectedDataSource?.value === "slack";
   }

   hasBigText = () => {
      return this.state.selectedDataSource?.value === "google_drive";
   }

   submit = () => {
      if (!this.state.selectedDataSource) return;

      let config = {};
      switch (this.state.selectedDataSource.value) {
         case "confluence":
            config = { url: this.state.newUrl, token: this.state.newToken } as ConfluenceConfig;
            break;
         case "slack":
            config = { token: this.state.newToken } as SlackConfig;
            break;
         case "google_drive":
            config = JSON.parse(this.state.newBigText)
            break;
      }

      let payload = {
         name: this.state.selectedDataSource.value,
         config: config
      }
      this.setState({ isAddingLoading: true });
      api.post(`/data-source/add`, payload).then(response => {
         toast.success("Data source added successfully, indexing...");
         this.props.onAdded(this.state.selectedDataSource.value);
         this.setState({isAddingLoading: false, isAdding: false, selectedDataSource: this.state.dataSourceTypes[0], newUrl: "", newToken: "", newBigText: ""  });
      }).catch(error => {
         toast.error("Error adding data source");
         this.setState({ isAddingLoading: false });
      });
   }

   onSelectChange = (event) => {
      this.setState({ selectedDataSource: event })
   }
}