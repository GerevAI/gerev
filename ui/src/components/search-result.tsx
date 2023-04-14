
import React from 'react';
import { Img } from 'react-image'

import PurpleFolder from '../assets/images/pur-dir.svg';
import GoogleDoc from '../assets/images/google-doc.svg';
import Docx from '../assets/images/docx.svg';
import Pptx from '../assets/images/pptx.svg';
import DefaultUserImage from '../assets/images/user.webp';
import Calendar from '../assets/images/calendar.svg';

import { DataSourceType } from '../data-source';
import { RiGitRepositoryLine } from 'react-icons/ri';
import { GoAlert } from 'react-icons/go';
import { MdVerified } from 'react-icons/md';

export interface TextPart {
    content: string
    bold: boolean
}

export enum ResultType {
    Docment = "document",
    Message = "message",
    Comment = "comment",
    Person = "person",
    Issue = "issue",
    GitPr = "git_pr"
}

export enum FileType {
    Docx = "docx",
    Pptx = "pptx",
    GoogleDoc = "doc",
}

export interface SearchResultDetails {
    type: ResultType
    data_source: string
    title: string
    author: string
    author_image_url: string
    author_image_data: string
    time: string
    content: TextPart[]
    score: number
    location: string
    platform: string
    file_type: FileType
    status: string
    is_active: boolean
    url: string
    child: SearchResultDetails
}


export interface SearchResultProps {
    resultDetails: SearchResultDetails
    dataSourceType: DataSourceType
}

export const SearchResult = (props: SearchResultProps) => {
    return (
        <div className={"mb-4 pt-2 " + (props.resultDetails.type !== ResultType.Comment ? "pt-3" : "")}>
            {props.resultDetails.type !== ResultType.Comment &&
                <span className="relative text-sm float-right text-white right-2 top-2">{props.resultDetails.score.toFixed(2)}%</span>}
            <div className="flex flex-row items-stretch">
                <span className='flex flex-col items-center mt-2 mr-2'>
                    {getBigIcon(props)}
                    {props.resultDetails.child && <span className={'w-[1px] mt-2 h-[85%] bg-[#66548D]'}></span>}

                </span>
                <p className='w-11/12 p-2 pt-0 ml-1 text-[#A3A3A3] text-sm font-poppins'>
                    <div className='flex flex-row items-center justify-start'>
                        {props.resultDetails.type === ResultType.Issue &&
                            <span className='mr-[6px] px-[7px] py-[1px] font-poppins font-medium text-[15px] bg-[#392E58] text-[#8F76C6] rounded-lg'>
                                ISSUE
                            </span>
                        }
                        <a className="text-[24px] overflow-hidden overflow-ellipsis whitespace-nowrap text-[#A78BF6] text-xl font-poppins font-medium hover:underline hover:cursor-pointer"
                            href={props.resultDetails.url} rel="noreferrer" target='_blank'>
                            {props.resultDetails.title}
                        </a>
                        {
                            props.resultDetails.type === ResultType.Comment && (
                                <span className='flex flex-row items-center justify-center ml-2 mt-[5px]'>
                                    Commented {getDaysAgo(props.resultDetails.time)}
                                </span>
                            )     
                        }
                        {
                            props.resultDetails.type === ResultType.Message && (
                                <span className='flex flex-row items-center justify-center ml-2 mt-[5px]'>
                                    Sent {getDaysAgo(props.resultDetails.time)}
                                </span>
                            )     
                        }
                        {props.resultDetails.type === ResultType.Issue &&
                            <span className={(isClosedStatus(props) ? 'bg-[#283328]' : 'bg-[#392E58]') + 
                            ' flex flex-row items-center ml-2 px-[7px] py-[1px] font-poppins font-medium text-[15px] text-[#8F76C6] rounded-lg'}>
                                {isClosedStatus(props) && 
                                <span className='flex flex-row items-center'>
                                    <MdVerified className='h-[16px] fill-[#79bd68]'></MdVerified>
                                    <span className='ml-1 overflow-hidden overflow-ellipsis whitespace-nowrap text-[#79bd68]'>{capitilize(props.resultDetails.status)}</span>
                                </span>
                                }
                                {isOpenStatus(props) && <GoAlert className='h-[14px] fill-[#ff9f2b]'></GoAlert>}
                                {!isClosedStatus(props) && <span className='ml-1 overflow-hidden overflow-ellipsis whitespace-nowrap'>{capitilize(props.resultDetails.status)}</span>}
                            </span>
                        }
                        {props.resultDetails.type === ResultType.Docment && props.resultDetails.file_type !== null &&
                            <span className='m-[6px] px-[7px] py-[1px] font-poppins font-medium text-[15px] bg-[#392E58] text-[#8F76C6] rounded-lg'>
                                {props.resultDetails.file_type.toUpperCase()}
                            </span>
                        }
                    </div>
                    {props.resultDetails.type !== ResultType.Comment && <span className="flex flex-row text-[16px] mb-4 mt-[6px] font-source-sans-pro font-semibold text-[#8F76C6]">
                        <span className="flex flex-row items-center leading-[17px] px-[5px] py-[2px] bg-[#382E56] rounded-[5px] ml-0 text-[#8F76C6]">
                            {
                                props.resultDetails.type === ResultType.Docment && <img alt="purple-folder"
                                    className="h-[12px]" src={PurpleFolder}></img>
                            }
                            {
                                props.resultDetails.type === ResultType.Issue &&
                                <RiGitRepositoryLine className='h-[14px] mt-[1px] mr-[2px]'></RiGitRepositoryLine>
                            }
                            <span className='text-[15x]'>
                                {props.resultDetails.type === ResultType.Docment && ' / '}
                                {props.resultDetails.type === ResultType.Message && '#'}
                                {props.resultDetails.location} </span>
                        </span>
                        {
                        props.resultDetails.type !== ResultType.Message &&
                            <span className="ml-1 flex flex-row items-center">
                                <Img alt="author" className="inline-block ml-[6px] mr-2 h-4 rounded-xl"
                                    src={[props.resultDetails.author_image_url, props.resultDetails.author_image_data, DefaultUserImage]}></Img>
                                <span className='capitalize'>{props.resultDetails.author} </span>
                            </span>
                        }
                        {props.resultDetails.child === null && props.resultDetails.type !== ResultType.Message && DateSpan(props)}
                        <span className="flex flex-row items-center">
                            &thinsp; |&thinsp;
                            <img alt="file-type" className="inline ml-2 mx-1  h-[12px] w-[12px] grayscale-[0.55]"
                                src={props.dataSourceType.image_base64}></img>
                            <span className="ml-[2px] ">{props.dataSourceType.display_name}</span>
                        </span>
                    </span>}
                    {
                        <span>
                            {props.resultDetails.content.map((text_part, index) => {
                                return (
                                    <span key={index} style={{ wordBreak: 'break-word' }} className={(text_part.bold ? 'font-bold text-white' : '') +
                                        " text-md font-poppins font-medium"}>
                                        {text_part.content}
                                    </span>
                                )
                            })}
                        </span>
                    }
                </p>
            </div>
            {props.resultDetails.child && <SearchResult resultDetails={props.resultDetails.child} dataSourceType={props.dataSourceType}></SearchResult>        
            }
        </div>
    );
}

function capitilize(str: string) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function isClosedStatus(props: SearchResultProps) {
    let closedStatuses = ['closed', 'resolved', 'done', 'completed', 'fixed', 'merged', 'finished', 'verified', 'approved', 'merged'];
    return (props.resultDetails.is_active !== null && props.resultDetails.is_active === false) || 
            closedStatuses.includes(props.resultDetails.status.toLowerCase());
}

function isOpenStatus(props: SearchResultProps) {
    let openStatuses = ['open', 'new', 'in progress', 'in review', 'in testing', 'in development', 'in qa', 'in staging'];
    return (props.resultDetails.is_active !== null && props.resultDetails.is_active === true) || 
            openStatuses.includes(props.resultDetails.status.toLowerCase());
}

function DateSpan(props: SearchResultProps) {
    const time = getFormattedDate(props.resultDetails.time);
    return (
        <span className='flex flex-row items-center ml-1'>
            <Img alt="author" className="inline-block ml-[6px] mr-1 h-4"
                src={Calendar}></Img>
            <span>&thinsp;
                {props.resultDetails.type === ResultType.Message ? 'Sent ' : 'Updated '}
                {time}</span>
        </span>
    )
}

function getDaysAgo(time: string) {
    let date = new Date(time);
    let now = new Date();
    let diff = Math.abs(now.getTime() - date.getTime());
    let days =  Math.floor(diff / (1000 * 3600 * 24));

    if (days === 0) {
        return 'today';
    } else  if (days === 1) {
        return '1 day ago';
    } else if (days < 365) {
        return days + ' days ago';
    } else if (days < 730) {
        return '1yr ago';
    } else {
        return Math.floor(days / 365) + 'yrs ago';
    }
}


function getFormattedDate(time: string) {
    let date = new Date(time);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}


function getBigIcon(props: SearchResultProps) {
    let containingClasses = "";
    let containingImage = "";
    let onTopImage = "";
    switch (props.resultDetails.type) {
        case ResultType.Docment:
        case ResultType.Issue:
        case ResultType.GitPr:
            if (props.resultDetails.file_type === null) {
                containingImage = props.dataSourceType.image_base64;
            } else {
                onTopImage = props.dataSourceType.image_base64;
                switch (props.resultDetails.file_type) {
                    case FileType.Docx:
                        containingImage = Docx;
                        break;
                    case FileType.Pptx:
                        containingImage = Pptx;
                        break;
                    case FileType.GoogleDoc:
                        containingImage = GoogleDoc;
                        break;
                }
            }
            break;
        case ResultType.Message:
            containingClasses = "rounded-full"
            containingImage = props.resultDetails.author_image_data ? props.resultDetails.author_image_data : props.resultDetails.author_image_url;
            onTopImage = props.dataSourceType.image_base64;
            break;
        case ResultType.Comment:
            containingClasses = "rounded-full"
            containingImage = props.resultDetails.author_image_data ? props.resultDetails.author_image_data : props.resultDetails.author_image_url;
            break;
    }
    if (onTopImage !== "") {
        return (
            <div className="mt-2 mr-[10px] drop-shadow-[0_0_25px_rgba(212,179,255,0.15)]">
                <Img height={"45px"} width={"45px"} className={containingClasses} alt="file-type" src={[containingImage, DefaultUserImage]} />
                <img alt="file-type" className="company-logo rounded-full p-[3px] h-[24px] w-[24px] absolute -right-[5px] -bottom-[5px] bg-white" src={onTopImage}></img>
            </div>
        )
    } else {
        return <Img height={"40px"} width={"40px"} alt="file-type" className={"drop-shadow-[0_0_25px_rgba(212,179,255,0.15)] " + containingClasses}
                src={[containingImage, DefaultUserImage]}></Img>
    }
}