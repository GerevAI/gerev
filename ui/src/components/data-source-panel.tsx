import * as React from "react";
import { Platform } from "./search-result";
import Select from 'react-select'
import { components } from 'react-select';

import Slack from '../assets/images/slack.svg';
import Confluence from '../assets/images/confluence.svg';
import { IoAddCircleOutline } from "react-icons/io5";
import { AiFillCheckCircle } from "react-icons/ai";
import { api } from "../api";


export interface DataSourceOption {
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
   isAdding: boolean
   dataSourceOptions: DataSourceOption[]
   selectedDataSource?: DataSourceOption
   newUrl: string
   newToken: string
}

export interface DataSourcePanelProps {
}

function getBigIconByPlatform(platform: Platform) {
   switch (platform) {
      case Platform.Confluence:
         return Confluence
      case Platform.Slack:
         return Slack;
   }
}

const Option = props => (
   <components.Option {...props}>
      <div className="flex flex-row w-10">
         <img className={"mr-2 h-[20px]"} src={getBigIconByPlatform(props.value)}></img>
         {props.label}

      </div>
   </components.Option>
);

export default class DataSourcePanel extends React.Component<DataSourcePanelProps, DataSourcePanelState> {

   constructor(props) {
      super(props);
      this.state = {
         isAdding: true,
         selectedDataSource: { value: 'confluence', label: 'Confluence' },
         dataSourceOptions: [
            { value: 'confluence', label: 'Confluence' },
            { value: 'slack', label: 'Slack' }
         ],
         newUrl: '',
         newToken: ''
      }
   }

   render() {
      return (

         <div className="relative flex flex-col bg-[#221f2e] items-start px-8 pt-0 pb-4">
            <h1 className="relative self-center text-white block text-4xl mb-8 font-poppins">Data Source Panel</h1>
            {
               !this.state.isAdding && (
                  <div>
                     <h1 className="text-2xl block text-white mb-4">Active data sources:</h1>
                     <div className="flex flex-row w-max">
                        {this.state.dataSourceOptions.map((data_source) => {
                           return (
                              <div className="flex py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#352C45] hover:shadow-inner shadow-blue-500/50 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
                                 <img className={"mr-2 h-[20px]"} src={getBigIconByPlatform(Platform[data_source.value])}></img>
                                 <h1 className="text-white">{data_source.value}</h1>
                                 <AiFillCheckCircle className="ml-6 text-[#9875d4] text-2xl"> </AiFillCheckCircle>
                              </div>
                           )
                        })
                        }
                        <div onClick={() => { this.setState({ isAdding: true }) }} className="flex py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#352C45] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#ffffff] border-b-[.5px] transition duration-300 ease-in-out">
                           <h1 className="text-white">Add</h1>
                           <IoAddCircleOutline className="ml-6 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                        </div>
                     </div>
                  </div>)
            }
            {
               this.state.isAdding && (
                  <div className="flex flex-col">
                     <div className="flex flex-row justify-center items-center mb-10 mt-5">
                        <h1 className="!my-0 mr-4 text-2xl block text-white mb-4">Select data source</h1>
                        <Select className="w-60" onChange={this.onSelectChange} value={this.state.selectedDataSource} options={this.state.dataSourceOptions} isDisabled={false} isSearchable={false} components={{ Option }} />
                     </div>
                     {
                        this.state.selectedDataSource && (
                           this.state.selectedDataSource.value === "confluence" && (
                              <div className="flex flex-col">
                                 <h1 className="text-2xl block text-white mb-4">Confluence</h1>
                                 <div className="flex flex-row">
                                    <div className="flex flex-col mr-10">
                                       <h1 className="text-lg block text-white mb-4">URL</h1>
                                       <input value={this.state.newUrl} onChange={(event) => this.setState({newUrl: event.target.value})} 
                                             className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2"></input>
                                    </div>
                                    <div className="flex flex-col">
                                       <h1 className="text-lg block text-white mb-4">Token</h1>
                                       <input value={this.state.newToken} onChange={(event) => this.setState({newToken: event.target.value})}
                                             className="w-96 h-10 rounded-lg bg-[#352C45] text-white p-2"></input>
                                    </div>
                                 </div>
                                 {/* add button */}
                                 <div className="flex flex-row justify-center items-center mt-10">
                                    <div className="flex py-2 pl-5 pr-3 m-2 flex-row items-center justify-center bg-[#352C45] hover:border-[#9875d4] rounded-lg font-poppins leading-[28px] border-[#ffffff] border-b-[.5px] transition duration-300 ease-in-out">
                                       <h1 className="text-white">Add</h1>
                                       <IoAddCircleOutline onClick={this.add} className="ml-6 text-white text-2xl hover:text-[#9875d4] hover:cursor-pointer transition duration-200 ease-in-out"></IoAddCircleOutline>
                                    </div>
                                 </div>
                              </div>
                           )

                        )
                     }
                  </div>
               )
            }

         </div>

      );
   }

   add() {
      if (!this.state.selectedDataSource) return;

      let config = {};
      switch (this.state.selectedDataSource.value) {
         case "confluence":
            config = {url: this.state.newUrl, token: this.state.newToken} as ConfluenceConfig;
         case "slack":
            config = {token: this.state.newToken} as SlackConfig;
      }

      let payload = {
         name: this.state.selectedDataSource.value,
         config: config
      }
      
      try {
         const response = api.post(`/data-source/add`, payload).then(response => {
            console.log(response);
         });
      } catch (error) {
         console.error(error);
      }

   }

   onSelectChange = (event) => {
      this.setState({ selectedDataSource: event })
   }
}