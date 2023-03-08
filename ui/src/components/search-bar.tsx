import * as React from "react";

import ClipLoader from "react-spinners/ClipLoader";
import { BsSearch, BsXLg } from "react-icons/bs";

export interface SearchBarState {
    suggestions: string[]
}

export interface SearchBarProps {
    query: string
    isLoading: boolean
    showReset: boolean
    onSearch: () => void
    onQueryChange: (query: string) => void
    onClear: () => void
}

export default class SearchBar extends React.Component <SearchBarProps, SearchBarState> {

    constructor(props) {
        super(props);
        this.state = {suggestions: []};
    }

    render() {
        return ( 
            <div className="h-[49.5px] w-[38%] rounded-b-[10px] rounded-t-[14px] bg-gradient-to-r from-[#8E59D1] via-[#85a6ec] to-[#b385ec]">
                <div className='flex h-12 w-full items-center container text-3xl rounded-[10px] bg-[#2A2A2A] text-[#C9C9C9]'>
                  
                  <button onClick={this.props.onSearch} className='mx-2 text-white p-2 rounded
                   hover:text-[#493294] transition duration-500 ease-in-out flex items-center'>
                    {this.props.isLoading ?
                    <ClipLoader
                      color="#ffffff"
                      loading={this.props.isLoading}
                      size={25}
                      aria-label="Loading Spinner"
                    /> : <BsSearch size={20} className="text-[#D2D2D2] hover:text-[#ebebeb] hover:cursor-pointer"></BsSearch>}
                  </button>
                  <input type="text" className='w-full font-poppins font-medium leading-7 text-lg p-2 rounded text-[#C9C9C9] bg-transparent !outline-none'
                         placeholder='Search' value={this.props.query} onChange={this.handleChange} onKeyDown={this.onKeyDown} />
                  {this.props.showReset &&
                    <BsXLg onClick={this.props.onClear} size={23} className='text-[#8E8C8C] mr-4 hover:text-[#c1bebe] hover:cursor-pointer'></BsXLg>
                  }
                </div>
              </div>
        ); 
    }

    onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
          this.props.onSearch();
        }
    }

    handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        this.props.onQueryChange(event.target.value);
    }

}
